import os
import json
import sqlite3
import threading
from datetime import datetime, timezone
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

FALLBACK_MODELS = [
    m.strip() for m in [
        os.environ.get("GROQ_REASONING_MODEL", ""),
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "gemma2-9b-it",
    ] if m.strip()
]

EXTRACTOR_MODELS = [
    m.strip() for m in [
        os.environ.get("GROQ_EXTRACTOR_MODEL", ""),
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile",
    ] if m.strip()
]

DB_PATH = os.environ.get("BRAIN_DB_PATH", "phoenix_brain.db").strip()
DB_LOCK = threading.Lock()


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


def call_groq_with_fallback(messages, models, temperature=0.55, max_tokens=700, json_mode=False):
    if not GROQ_API_KEY:
        return "నమస్తే రాజేష్! సర్వర్‌లో GROQ_API_KEY సెట్ చేయాలి—అది సెట్ చేస్తే నేను వెంటనే ఫుల్ స్పీడ్‌లో మాట్లాడతాను."

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    last_error = ""
    seen = set()
    for model in models:
        if model in seen:
            continue
        seen.add(model)

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
                        return content
            else:
                last_error = f"{model} -> HTTP {resp.status_code}: {resp.text[:160]}"
        except Exception as exc:
            last_error = f"{model} -> {str(exc)[:160]}"

    return f"క్షమించండి రాజేష్, ఇప్పుడే Groq సర్వర్ నుండి సమాధానం రావడంలో చిన్న సమస్య వచ్చింది ({last_error}). ఒక్కసారి మళ్లీ ప్రయత్నించండి."


def get_short_term_history(user_id, limit=8):
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


def get_relevant_memories(user_id, query="", limit=10):
    try:
        with DB_LOCK:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            cur = conn.cursor()
            cur.execute(
                """
                SELECT category, fact FROM user_memories
                WHERE user_id = ?
                ORDER BY id DESC LIMIT 40
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
        return [f"[{cat}] {fact}" for _, cat, fact in ranked[:limit]]
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
                    fact = str(item.get("fact", "")).strip()
                    category = str(item.get("category", "general")).strip() or "general"
                else:
                    fact = str(item).strip()
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
        raw_json = call_groq_with_fallback(
            messages=[
                {"role": "system", "content": extractor_prompt},
                {"role": "user", "content": f"User: {user_text}\nAssistant: {assistant_reply}"},
            ],
            models=EXTRACTOR_MODELS,
            temperature=0.1,
            max_tokens=250,
            json_mode=True,
        )
        parsed = json.loads(raw_json)
        memories = parsed.get("memories")
        if isinstance(memories, list) and memories:
            save_extracted_facts(user_id, memories)
    except Exception as exc:
        print(f"[Background Extractor Warning]: {exc}")


def run_ai_brain(user_id, user_text, mood="neutral", current_time=None):
    if not current_time:
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    memories = get_relevant_memories(user_id, query=user_text)
    history = get_short_term_history(user_id, limit=8)
    memory_text = "\n".join(f"- {m}" for m in memories) if memories else "- ఇంకా ప్రత్యేక జ్ఞాపకాలు లేవు."

    system_prompt = f"""
నీవు PHOENIX యాప్‌లోని అత్యంత ఇంటిలిజెంట్, శక్తివంతమైన AI బ్రెయిన్.
యూజర్ మాట్లాడే భాషకు తగ్గట్టుగా (ముఖ్యంగా సహజమైన తెలుగులో లేదా యూజర్ అడిగిన భాషలో) స్పష్టంగా, ఆప్యాయంగా, ఆచరణాత్మకంగా సమాధానం ఇవ్వు.

[Long-Term Memory]
{memory_text}

[సందర్భం]
- సమయం: {current_time}
- యూజర్ మూడ్: {mood}

[నియమాలు]
1. యూజర్ ప్రశ్న, మూడ్, సందర్భాన్ని బట్టి సహజంగా, స్పష్టంగా మాట్లాడు.
2. Long-Term Memory లోని విషయాలను అవసరమైనప్పుడు మాత్రమే ఉపయోగించు.
3. సమాధానం పొడవైన ఉపన్యాసంలా కాకుండా సూటిగా, ఉపయోగకరంగా ఉండాలి.
""".strip()

    messages = [{"role": "system", "content": system_prompt}]
    for turn in history:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": user_text})

    reply = call_groq_with_fallback(
        messages=messages,
        models=FALLBACK_MODELS,
        temperature=0.55,
        max_tokens=700,
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


def format_app_payload(text):
    return jsonify({
        "status": "success",
        "reply": text,
        "response": text,
        "answer": text,
        "message": text,
        "text": text,
        "result": text,
        "output": text,
    }), 200


def handle_brain_request():
    user_text, user_id, mood, current_time = extract_incoming_data()
    if not user_text:
        return format_app_payload("నమస్తే రాజేష్! నేను PHOENIX ని. ఏదైనా అడుగు, నేను రెడీగా ఉన్నాను.")

    try:
        reply = run_ai_brain(
            user_id=user_id,
            user_text=user_text,
            mood=mood,
            current_time=current_time,
        )
        return format_app_payload(reply)
    except Exception as exc:
        return format_app_payload(f"నమస్తే రాజేష్! ఇప్పుడు చిన్న సమస్య వచ్చింది: {str(exc)[:180]}")


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
    return jsonify({"status": "ok", "groq_key_set": bool(GROQ_API_KEY)}), 200


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
