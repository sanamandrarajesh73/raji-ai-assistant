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

TELUGU_START = chr(0x0C00)
TELUGU_END = chr(0x0C7F)


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
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()
            conn.close()
    except Exception as exc:
        print(f"[DB Init Warning]: {exc}")


init_db()


def clean_text_for_app(text, fallback_name="మిత్రమా"):
    default_msg = f"చెప్పండి {fallback_name}, నేను పూర్తి శక్తితో సిద్ధంగా ఉన్నాను. ఇప్పుడు ఏం చేయమంటారు {fallback_name}?"
    if not text:
        return default_msg
    s = str(text)
    s = s.replace("\\r\\n", " ").replace("\\n", " ").replace("\\r", " ").replace("\\t", " ")
    s = s.replace("\r\n", " ").replace("\n", " ").replace("\r", " ").replace("\t", " ")
    s = re.sub(r"\*\*(.*?)\*\*", r"\1", s)
    s = s.replace("**", "").replace("__", "").replace("```", "").replace("`", "")
    s = re.sub(r"^#{1,6}\s*", "", s)
    allowed_pattern = rf"[^\w\s{TELUGU_START}-{TELUGU_END}.,!?():;/\-–—'\"%+=@#&]"
    s = re.sub(allowed_pattern, " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return default_msg
    return s


def get_user_display_name(user_id):
    try:
        with DB_LOCK:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            cur = conn.cursor()
            cur.execute("SELECT display_name FROM user_profiles WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            conn.close()
        if row and str(row[0]).strip():
            return str(row[0]).strip()
    except Exception:
        pass
    return "మిత్రమా"


def set_user_display_name(user_id, name):
    name_clean_pattern = rf"[^\w\s{TELUGU_START}-{TELUGU_END}]"
    cleaned = re.sub(name_clean_pattern, "", str(name or "")).strip()
    if not cleaned or len(cleaned) > 40:
        return
    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        with DB_LOCK:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO user_profiles (user_id, display_name, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET display_name = excluded.display_name, updated_at = excluded.updated_at
                """,
                (user_id, cleaned, now_iso),
            )
            conn.commit()
            conn.close()
    except Exception as exc:
        print(f"[Profile Save Warning]: {exc}")


def maybe_extract_name_from_text(user_id, text):
    if not text:
        return
    patterns = [
        rf"(?:నా పేరు|నా పేరే|నన్ను)\s+([{TELUGU_START}-{TELUGU_END}A-Za-z]{{2,25}})(?:\s+అని\s+పిలువు|\s+అంటారు|\s+అండి|\s+అని|\s*$)",
        rf"(?:my name is|call me)\s+([A-Za-z{TELUGU_START}-{TELUGU_END}]{{2,25}})(?:\s|$|\.)",
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()
            blocked = {"ఎవరు", "ఏంటి", "తెలుసా", "చెప్పు", "ఏమి", "who", "what"}
            if candidate.lower() not in blocked:
                set_user_display_name(user_id, candidate)
                return


def is_multi_choice_decision(text):
    if not text:
        return False
    q_low = text.lower()
    choice_cues = [
        "ఏది మంచిది", "ఏది ఎంచుకోవాలి", "ఏది తీసుకోవాలి", "ఎలా నిర్ణయించాలి",
        "గందరగోళం", "కన్ఫ్యూజన్", "రెండు", "ఎంపిక", "ఆప్షన్", "కోర్సు",
        "పెట్టుబడి", "వ్యాపారం", "టీమ్", "నిర్ణయం", "లేదా", "గెలుస్తుందా",
        "అంచనా", " vs ", " or ", "which one", "choose", "decision",
        "confused", "invest", "course", "team", "win"
    ]
    return any(cue in text or cue in q_low for cue in choice_cues)


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


def call_groq_direct(messages, temperature=0.45, max_tokens=360, json_mode=False, fallback_name="మిత్రమా"):
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
                        return content if json_mode else clean_text_for_app(content, fallback_name=fallback_name)
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


def save_extracted_facts(user_id, facts_list, fallback_name="మిత్రమా"):
    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        with DB_LOCK:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            cur = conn.cursor()
            for item in facts_list:
                if isinstance(item, dict):
                    fact = clean_text_for_app(str(item.get("fact", "")), fallback_name=fallback_name)
                    category = str(item.get("category", "general")).strip() or "general"
                else:
                    fact = clean_text_for_app(str(item), fallback_name=fallback_name)
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


def background_extract_facts(user_id, user_text, assistant_reply, fallback_name="మిత్రమా"):
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
            max_tokens=180,
            json_mode=True,
            fallback_name=fallback_name,
        )
        parsed = json.loads(raw_json)
        memories = parsed.get("memories")
        if isinstance(memories, list) and memories:
            save_extracted_facts(user_id, memories, fallback_name=fallback_name)
    except Exception as exc:
        print(f"[Background Extractor Warning]: {exc}")


def run_phoenix_brain(user_id, user_text, mood="neutral", current_time=None, explicit_name=""):
    if not current_time:
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if explicit_name:
        set_user_display_name(user_id, explicit_name)
    maybe_extract_name_from_text(user_id, user_text)
    user_name = get_user_display_name(user_id)

    q_low = user_text.lower()
    if ("హాట్" in user_text or "హార్ట్" in user_text or "heart" in q_low) and (
        "సింబల్" in user_text or "బొమ్మ" in user_text or "గీయ" in user_text or "చూపి" in user_text or "draw" in q_low
    ):
        reply = clean_text_for_app(
            f"చెప్పండి {user_name}, హార్ట్ బొమ్మను పేపర్ మీద సులభంగా గీయడానికి మూడు చిన్న స్టెప్స్: "
            f"ఒకటి, పైన పక్కపక్కనే రెండు చిన్న గుండ్రని ఆర్చ్‌లు గీయండి. "
            f"రెండు, ఆ రెండు ఆర్చ్‌ల మధ్యలో చిన్న మలుపు ఇచ్చి, కిందికి వంపుగా రెండు గీతలు లాగండి. "
            f"మూడు, ఆ రెండు గీతలు కింద ఒక బిందువు వద్ద కలిసేలా గీస్తే నీట్ హార్ట్ రెడీ. "
            f"ఇప్పుడు ఏం చేయమంటారు {user_name}?",
            fallback_name=user_name,
        )
        save_message(user_id, "user", user_text, mood=mood)
        save_message(user_id, "assistant", reply, mood="helpful")
        return reply

    memories = get_relevant_memories(user_id, query=user_text)
    history = get_short_term_history(user_id, limit=6)
    memory_text = "\n".join(f"- {m}" for m in memories) if memories else "- ఇంకా ప్రత్యేక జ్ఞాపకాలు లేవు."

    decision_mode = is_multi_choice_decision(user_text)
    decision_instructions = """
[బహుళ ఎంపికల విశ్లేషణ నియమాలు]
యూజర్ రెండు లేదా అంతకంటే ఎక్కువ ఎంపికల (క్రికెట్ టీమ్‌లు, వ్యాపార అవకాశాలు, పెట్టుబడి ఎంపికలు, జీవిత నిర్ణయాలు, కోర్సులు) మధ్య గందరగోళంలో ఉన్నప్పుడు ఈ క్రింది అంశాలను స్పష్టంగా, లోకజ్ఞానంతో, వివేకంతో వివరించు:
1. అందుబాటులో ఉన్న సమాచారాన్ని ఆధారంగా చేసుకుని ప్రతి ఎంపికను విడివిడిగా విశ్లేషించు.
2. యూజర్ భావోద్వేగం, అభిమానం లేదా తొందరపాటుకు, అసలు వాస్తవ సమాచారానికి మధ్య ఉన్న తేడాను స్పష్టంగా చూపించు.
3. ఈ నిర్ణయంలో ఇంకా ఏ అంశాలు తెలియకుండా ఉన్నాయో (ఉదాహరణకు తాజా సమాచారం, వ్యక్తిగత బడ్జెట్, శక్తి, కాలపరిమితి) నిజాయితీగా చెప్పు.
4. ప్రతి ఎంపిక వల్ల వచ్చే సాధ్యమైన ఫలితాలు, అలాగే ప్రమాదాలు లేదా నష్టాలను సమతుల్యంగా వివరించు.
5. నిర్ణయం తీసుకునే ముందు యూజర్ ఆలోచించాల్సిన ముఖ్యమైన అంశాలను సూచించు.
6. అత్యంత కఠిన నియమం: ఏ ఎంపిక ఎంచుకున్నా తప్పకుండా గెలుస్తుందని లేదా లాభమే వస్తుందని ఎప్పుడూ హామీ ఇవ్వకు. ఫలితం అనిశ్చితమని, తుది నిర్ణయం యూజర్ విచక్షణ మరియు పరిస్థితులపై ఆధారపడి ఉంటుందని స్పష్టంగా చెప్పు.
""".strip() if decision_mode else ""

    system_prompt = f"""
నీవు PHOENIX యాప్‌లోని అత్యంత శక్తివంతమైన, వివేకవంతమైన, లోకజ్ఞానం కలిగిన జార్విస్ (JARVIS) లాంటి సహాయకుడివి.
ప్రస్తుతం ఈ యాప్ వాడుతున్న వ్యక్తి పేరు {user_name}. నువ్వు ఎప్పుడూ ఆ వ్యక్తి పేరునే ({user_name}) ఉపయోగించి గౌరవంగా, ఆప్యాయంగా, చురుగ్గా పలకరించాలి.

[జ్ఞాపకాలు]
{memory_text}

[సందర్భం]
- సమయం: {current_time}
- యూజర్ పేరు: {user_name}
- యూజర్ మూడ్: {mood}

[జార్విస్ నియమాలు]
1. సహజమైన, రోజువారీ మాట్లాడే తెలుగులో (లేదా యూజర్ ఏ భాషలో అడిగితే ఆ భాషలో—ఇంగ్లీష్, తమిళం, హిందీ, కన్నడతో సహా) పవర్‌ఫుల్‌గా, క్లియర్‌గా, స్నేహపూర్వకంగా సమాధానం ఇవ్వు.
2. సమాధానంలో యూజర్‌ని {user_name} అని పిలుస్తూ, "చెప్పండి {user_name}", "ఇప్పుడు ఏం చేయమంటారు {user_name}" లాంటి సహజమైన జార్విస్ శైలిని ఉపయోగించు. (ఒకవేళ యూజర్ తన పేరు మార్చమని లేదా వేరే పేరు చెబితే, ఆ కొత్త పేరునే వాడు).
3. సమాధానం చాలా పొడవుగా కాకుండా, సూటిగా, స్పష్టంగా, నీట్‌గా ఒకే పారాగ్రాఫ్‌లో ఉండేలా రాయ్.
4. కృత్రిమంగా, పుస్తకపు పదాలు ("శాస్త్రం", "విజ్ఞానశాస్త్రం") లేదా స్టార్ గుర్తులు (**), హ్యాష్‌లు (#), ASCII బొమ్మలు అసలు వాడకు.
5. ఏ విషయంలోనూ 100% గెలుపు లేదా లాభం వస్తుందని తప్పుడు హామీ ఇవ్వకు; వాస్తవాలు, రిస్క్‌లు, ఆలోచించాల్సిన అంశాలను నిజాయితీగా చూపించు.

{decision_instructions}
""".strip()

    messages = [{"role": "system", "content": system_prompt}]
    for turn in history:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": user_text})

    reply = call_groq_direct(
        messages=messages,
        temperature=0.45,
        max_tokens=360 if decision_mode else 260,
        json_mode=False,
        fallback_name=user_name,
    )

    save_message(user_id, "user", user_text, mood=mood)
    save_message(user_id, "assistant", reply, mood="helpful")

    threading.Thread(
        target=background_extract_facts,
        args=(user_id, user_text, reply, user_name),
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
    explicit_name = str(src.get("user_name") or src.get("userName") or src.get("name") or "").strip()
    mood = str(src.get("mood") or src.get("voice_emotion") or src.get("emotion") or "neutral").strip() or "neutral"
    current_time = src.get("current_time") or src.get("time")
    return user_text, user_id, mood, current_time, explicit_name


def build_response(reply_text, fallback_name="మిత్రమా"):
    clean_reply = clean_text_for_app(reply_text, fallback_name=fallback_name)
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
    user_text, user_id, mood, current_time, explicit_name = extract_incoming_data()
    if not user_text:
        user_text = "నమస్తే"

    user_name = explicit_name or get_user_display_name(user_id)

    try:
        reply = run_phoenix_brain(
            user_id=user_id,
            user_text=user_text,
            mood=mood,
            current_time=current_time,
            explicit_name=explicit_name,
        )
        return build_response(reply, fallback_name=user_name)
    except Exception as exc:
        err_reply = clean_text_for_app(
            f"చెప్పండి {user_name}, ఇప్పుడు చిన్న సమస్య వచ్చింది: {str(exc)[:150]}",
            fallback_name=user_name,
        )
        return build_response(err_reply, fallback_name=user_name)


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
