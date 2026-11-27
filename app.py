import os
import re
import json
import sqlite3
import threading
from datetime import datetime, timezone
import requests
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_CHAT_URL = f"{GROQ_BASE_URL}/chat/completions"
GROQ_MODELS_URL = f"{GROQ_BASE_URL}/models"

PREFERRED_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3-32b",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
]

DB_PATH = os.environ.get("BRAIN_DB_PATH", "phoenix_brain.db").strip()
DB_LOCK = threading.Lock()
_CACHED_MODELS = []
_MODELS_LOCK = threading.Lock()


def init_db():
    try:
        with DB_LOCK:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    mood TEXT DEFAULT 'neutral',
                    created_at TEXT NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    fact TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(user_id, fact)
                )
            """)
            conn.commit()
            conn.close()
    except Exception as exc:
        print(f"[DB Init Warning]: {exc}")


init_db()


def clean_text_for_app(text):
    if not text:
        return "చెప్పండి రాజేష్, నేను పూర్తి శక్తితో సిద్ధంగా ఉన్నాను. ఇప్పుడు ఏం చేయమంటారు రాజేష్?"
    s = str(text)
    # Escaped newlines ను అసలు newline గా మార్చడం (బొమ్మల ఆకారం చెడిపోకుండా ఉండటానికి)
    s = s.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\r", "\n").replace("\\t", " ")
    s = s.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    # Markdown bold/headings తొలగించడం (కానీ * - / \ | _ + = లాంటి డ్రాయింగ్ అక్షరాలను ఉంచడం)
    s = re.sub(r"\*\*(.*?)\*\*", r"\1", s)
    s = s.replace("__", "").replace("```", "").replace("`", "")
    s = re.sub(r"^#{1,6}\s*", "", s, flags=re.MULTILINE)
    # తెలుగు అక్షరాలు, ఇంగ్లీష్, అంకెలు, మరియు ASCII డ్రాయింగ్ చిహ్నాలు మాత్రమే ఉంచడం
    s = re.sub(r"[^\w\s\n\u0C00-\u0C7F.,!?():;/\\|\-_+*=@#&'\"%<>^~]", " ", s)
    # ప్రతి లైన్‌ను శుభ్రం చేస్తూ, డ్రాయింగ్ కోసం ముందుండే స్పేస్‌లను కాపాడటం
    cleaned_lines = []
    for line in s.split("\n"):
        line_clean = line.rstrip()
        cleaned_lines.append(line_clean)
    s = "\n".join(cleaned_lines)
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    if not s:
        return "చెప్పండి రాజేష్, మీ కోసం ఎప్పుడూ సిద్ధంగా ఉన్నాను. ఇప్పుడు ఏం చేయమంటారు రాజేష్?"
    return s


def get_active_groq_models():
    global _CACHED_MODELS
    if not GROQ_API_KEY:
        return PREFERRED_MODELS

    with _MODELS_LOCK:
        if _CACHED_MODELS:
            return list(_CACHED_MODELS)

        discovered = []
        try:
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
            resp = requests.get(GROQ_MODELS_URL, headers=headers, timeout=15)
            if resp.status_code < 400:
                items = (resp.json() or {}).get("data") or []
                for item in items:
                    mid = str(item.get("id", "")).strip()
                    if not mid:
                        continue
                    low = mid.lower()
                    if any(skip in low for skip in ("whisper", "tts", "playai", "guard", "embed", "moderation")):
                        continue
                    discovered.append(mid)
        except Exception as exc:
            print(f"[Models Discovery Warning]: {exc}")

        ordered = []
        for pref in PREFERRED_MODELS:
            if not discovered or pref in discovered:
                if pref not in ordered:
                    ordered.append(pref)
        for mid in discovered:
            if mid not in ordered:
                ordered.append(mid)

        _CACHED_MODELS = ordered if ordered else list(PREFERRED_MODELS)
        return list(_CACHED_MODELS)


def call_groq_direct(messages, temperature=0.45, max_tokens=360, json_mode=False):
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set in Render Environment.")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    models = get_active_groq_models()
    errors = []

    for model in models:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            resp = requests.post(GROQ_CHAT_URL, headers=headers, json=payload, timeout=35)
            if resp.status_code < 400:
                data = resp.json()
                choices = data.get("choices") or []
                if choices:
                    content = (choices[0].get("message", {}).get("content") or "").strip()
                    if content:
                        return content if json_mode else clean_text_for_app(content)
            else:
                err_txt = resp.text[:160]
                errors.append(f"{model}: HTTP {resp.status_code} - {err_txt}")
                if resp.status_code == 404 or "does not exist" in err_txt.lower():
                    global _CACHED_MODELS
                    with _MODELS_LOCK:
                        _CACHED_MODELS = [m for m in _CACHED_MODELS if m != model]
        except Exception as exc:
            errors.append(f"{model}: {str(exc)[:150]}")

    raise RuntimeError(" | ".join(errors[-2:]) if errors else "Groq API failed.")


def get_short_term_history(user_id, limit=6):
    try:
        with DB_LOCK:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            cur = conn.cursor()
            cur.execute(
                """
                SELECT role, content FROM chat_history
                WHERE user_id = ?
                ORDER BY id DESC LIMIT ?
                """,
                (user_id, limit),
            )
            rows = cur.fetchall()
            conn.close()
        rows.reverse()
        return [{"role": r[0], "content": r[1]} for r in rows]
    except Exception:
        return []


def save_message(user_id, role, content, mood="neutral"):
    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        with DB_LOCK:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO chat_history (user_id, role, content, mood, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, role, content, mood, now_iso),
            )
            conn.commit()
            conn.close()
    except Exception as exc:
        print(f"[Save Message Warning]: {exc}")


def get_relevant_memories(user_id, query="", limit=8):
    try:
        with DB_LOCK:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            cur = conn.cursor()
            cur.execute(
                """
                SELECT category, fact FROM user_memories
                WHERE user_id = ?
                ORDER BY id DESC LIMIT 30
                """,
                (user_id,),
            )
            rows = cur.fetchall()
            conn.close()

        if not rows:
            return []

        query_tokens = {w.lower() for w in query.split() if len(w) > 2}
        ranked = []
        for idx, (cat, fact) in enumerate(rows):
            fact_tokens = {w.lower() for w in fact.split() if len(w) > 2}
            overlap = len(query_tokens & fact_tokens)
            score = overlap * 10 + max(0, 20 - idx)
            ranked.append((score, cat, fact))

        ranked.sort(key=lambda item: item[0], reverse=True)
        return [f"{fact}" for _, _, fact in ranked[:limit]]
    except Exception:
        return []


def save_extracted_facts(user_id, facts_list):
    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        with DB_LOCK:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            cur = conn.cursor()
            for item in facts_list:
                if isinstance(item, dict):
                    fact = clean_text_for_app(str(item.get("fact", "")))
                    category = str(item.get("category", "general")).strip() or "general"
                else:
                    fact = clean_text_for_app(str(item))
                    category = "general"

                if fact:
                    cur.execute(
                        """
                        INSERT OR IGNORE INTO user_memories (user_id, category, fact, created_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (user_id, category, fact, now_iso),
                    )
            conn.commit()
            conn.close()
    except Exception as exc:
        print(f"[Save Facts Warning]: {exc}")


def background_extract_facts(user_id, user_text, assistant_reply):
    if not GROQ_API_KEY:
        return
    try:
        extractor_prompt = (
            "యూజర్ సంభాషణ నుండి భవిష్యత్తులో గుర్తుంచుకోవాల్సిన ముఖ్యమైన విషయాలు మాత్రమే తీయండి. "
            'JSON మాత్రమే ఇవ్వండి: {"memories": [{"category": "preference|goal|project|habit|key_fact", "fact": "చిన్న వాక్యం"}]}'
        )
        raw_json = call_groq_direct(
            messages=[
                {"role": "system", "content": extractor_prompt},
                {"role": "user", "content": f"User: {user_text}\nAssistant: {assistant_reply}"},
            ],
            temperature=0.1,
            max_tokens=200,
            json_mode=True,
        )
        parsed = json.loads(raw_json)
        memories = parsed.get("memories")
        if isinstance(memories, list) and memories:
            save_extracted_facts(user_id, memories)
    except Exception as exc:
        print(f"[Background Extractor Warning]: {exc}")


def run_phoenix_brain(user_id, user_text, mood="neutral", current_time=None):
    if not current_time:
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    memories = get_relevant_memories(user_id, query=user_text)
    history = get_short_term_history(user_id, limit=6)
    memory_text = "\n".join(f"- {m}" for m in memories) if memories else "- ఇంకా ప్రత్యేక జ్ఞాపకాలు లేవు."

    system_prompt = f"""
నీవు PHOENIX యాప్‌లోని అత్యంత శక్తివంతమైన జార్విస్ (JARVIS) లాంటి సహాయకుడివి.
నీ యూజర్ పేరు రాజేష్. అతని కోసం ఎప్పుడూ చురుగ్గా, నమ్మకంగా, ఆప్యాయంగా, పవర్‌ఫుల్‌గా పనిచేసే పర్సనల్ అసిస్టెంట్‌వి.

[జ్ఞాపకాలు]
{memory_text}

[సందర్భం]
- సమయం: {current_time}
- యూజర్ మూడ్: {mood}

[జార్విస్ నియమాలు]
1. రాజేష్‌తో మాట్లాడేటప్పుడు సహజమైన, రోజువారీ మాట్లాడే తెలుగులో (లేదా రాజేష్ ఏ భాషలో అడిగితే ఆ భాషలో) పవర్‌ఫుల్‌గా, క్లియర్‌గా, స్నేహపూర్వకంగా సమాధానం ఇవ్వు.
2. సమాధానంలో రాజేష్‌ని గౌరవంగా, ఆప్యాయంగా పలకరించు. ఉదాహరణకు "చెప్పండి రాజేష్", "ఇప్పుడు ఏం చేయమంటారు రాజేష్" లాంటి సహజమైన శైలిని ఉపయోగించు.
3. సాధారణ ప్రశ్నలకు 3-4 చిన్న వాక్యాల్లో సూటిగా, నీట్‌గా సమాధానం ఇవ్వు. కృత్రిమంగా, పుస్తకపు పదాలు ("శాస్త్రం", "విజ్ఞానశాస్త్రం") వాడకు.
4. డ్రాయింగ్ / బొమ్మ / సింబల్ రూల్: ఎవరైనా ఏదైనా బొమ్మ గీయమని లేదా సింబల్ (హార్ట్, స్టార్, ఇల్లు, పువ్వు, ఆకారాలు) చూపించమని అడిగితే, ముందుగా ఇంగ్లీష్ అక్షరాలు (A, B, C, O, V, M) లేదా అంకెలు (1, 2, 3) మరియు సాధారణ గీతలతో (*, -, /, \, |) చిన్న, స్పష్టమైన చేతి గీతల నమూనా బొమ్మ (ASCII Sketch) గీసి చూపించు. ఆ తర్వాత దాన్ని పేపర్ మీద చేత్తో సులభంగా ఎలా గీయాలో 2-3 చిన్న స్టెప్స్‌లో చెప్పు.
5. మార్క్‌డౌన్ స్టార్ గుర్తులు (**), హ్యాష్‌లు (#), కోడ్ బ్లాక్‌లు (```) అసలు వాడకు.
""".strip()

    messages = [{"role": "system", "content": system_prompt}]
    for turn in history:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": user_text})

    reply = call_groq_direct(
        messages=messages,
        temperature=0.45,
        max_tokens=360,
        json_mode=False,
    )

    save_message(user_id, "user", user_text, mood=mood)
    save_message(user_id, "assistant", reply, mood="helpful")

    threading.Thread(
        target=background_extract_facts,
        args=(user_id, user_text, reply),
        daemon=True,
    ).start()

    return reply


def extract_incoming_data():
    if request.method == "GET":
        src = request.args
    else:
        src = request.get_json(silent=True)
        if not isinstance(src, dict) or not src:
            src = request.form.to_dict() if request.form else {}

    user_text = str(
        src.get("query")
        or src.get("message")
        or src.get("prompt")
        or src.get("text")
        or src.get("q")
        or src.get("input")
        or ""
    ).strip()

    user_id = str(src.get("user_id") or src.get("userId") or "phoenix_user").strip() or "phoenix_user"
    mood = str(src.get("mood") or src.get("voice_emotion") or src.get("emotion") or "neutral").strip() or "neutral"
    current_time = src.get("current_time") or src.get("time")
    return user_text, user_id, mood, current_time


def build_response(reply_text):
    clean_reply = clean_text_for_app(reply_text)
    wants_plain = str(request.args.get("format", "")).strip().lower() in ("text", "plain", "raw")
    accept_header = str(request.headers.get("Accept", "")).lower()
    if wants_plain or ("text/plain" in accept_header and "application/json" not in accept_header):
        return Response(clean_reply, status=200, mimetype="text/plain; charset=utf-8")

    return jsonify({
        "status": "success",
        "reply": clean_reply,
        "response": clean_reply,
        "answer": clean_reply,
        "message": clean_reply,
        "text": clean_reply,
        "result": clean_reply,
        "output": clean_reply,
        "content": clean_reply,
        "data": clean_reply,
    }), 200


def handle_brain_request():
    user_text, user_id, mood, current_time = extract_incoming_data()
    if not user_text:
        user_text = "నమస్తే"

    try:
        reply = run_phoenix_brain(
            user_id=user_id,
            user_text=user_text,
            mood=mood,
            current_time=current_time,
        )
        return build_response(reply)
    except Exception as exc:
        err_reply = clean_text_for_app(f"చెప్పండి రాజేష్, ఇప్పుడు చిన్న సమస్య వచ్చింది: {str(exc)[:150]}")
        return build_response(err_reply)


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        return handle_brain_request()
    return jsonify({
        "status": "live",
        "app": "PHOENIX AI Brain",
        "groq_key_set": bool(GROQ_API_KEY),
    }), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "groq_key_set": bool(GROQ_API_KEY),
        "models": get_active_groq_models()[:3],
    }), 200


@app.route("/run", methods=["GET", "POST"])
@app.route("/chat", methods=["GET", "POST"])
@app.route("/ask", methods=["GET", "POST"])
@app.route("/api/chat", methods=["GET", "POST"])
@app.route("/api/ask", methods=["GET", "POST"])
@app.route("/generate", methods=["GET", "POST"])
@app.route("/phoenix", methods=["GET", "POST"])
@app.route("/brain", methods=["GET", "POST"])
@app.route("/v1/chat", methods=["GET", "POST"])
def chat_routes():
    return handle_brain_request()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
            
