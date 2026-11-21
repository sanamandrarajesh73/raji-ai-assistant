import os
import json
import sqlite3
import threading
from datetime import datetime, timezone
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

# Gunicorn (gunicorn --timeout 120 app:app) కోసం టాప్-లెవల్ Flask app
app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

REASONING_MODEL = os.environ.get("GROQ_REASONING_MODEL", "llama-3.3-70b-versatile").strip()
EXTRACTOR_MODEL = os.environ.get("GROQ_EXTRACTOR_MODEL", "llama-3.1-8b-instant").strip()

DB_PATH = os.environ.get("BRAIN_DB_PATH", "phoenix_brain.db").strip()
DB_LOCK = threading.Lock()


def init_db():
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


init_db()


def call_groq_api(messages, model, temperature=0.55, max_tokens=700, json_mode=False):
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is missing in Render Environment.")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    resp = requests.post(GROQ_CHAT_URL, headers=headers, json=payload, timeout=40)
    if resp.status_code >= 400:
        raise RuntimeError(f"Groq API Error ({resp.status_code}): {resp.text[:300]}")

    data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("Groq API returned empty choices.")
    return (choices[0].get("message", {}).get("content") or "").strip()


def get_short_term_history(user_id, limit=8):
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


def save_message(user_id, role, content, mood="neutral"):
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


def get_relevant_memories(user_id, query="", limit=10):
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


def save_extracted_facts(user_id, facts_list):
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


def background_extract_facts(user_id, user_text, assistant_reply):
    try:
        extractor_prompt = (
            "యూజర్ సంభాషణ నుండి భవిష్యత్తులో గుర్తుంచుకోవాల్సిన ముఖ్యమైన, స్థిరమైన విషయాలు మాత్రమే తీయండి "
            "(preferences, goals, projects, habits, key_facts). 'hi', 'ok', 'thanks' లాంటి తాత్కాలిక మాటలు వద్దు. "
            'JSON మాత్రమే ఇవ్వండి: {"memories": [{"category": "preference|goal|project|habit|key_fact", "fact": "చిన్న స్పష్టమైన వాక్యం"}]}'
        )
        conversation_text = f"User: {user_text}\nAssistant: {assistant_reply}"
        raw_json = call_groq_api(
            messages=[
                {"role": "system", "content": extractor_prompt},
                {"role": "user", "content": conversation_text},
            ],
            model=EXTRACTOR_MODEL,
            temperature=0.1,
            max_tokens=250,
            json_mode=True,
        )
        parsed = json.loads(raw_json)
        memories = parsed.get("memories")
        if isinstance(memories, list) and memories:
            save_extracted_facts(user_id, memories)
    except Exception as exc:
        print(f"[Background Memory Extractor Warning]: {exc}")


def run_ai_brain(user_id, user_text, mood="neutral", current_time=None):
    if not current_time:
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    memories = get_relevant_memories(user_id, query=user_text)
    history = get_short_term_history(user_id, limit=8)

    memory_text = "\n".join(f"- {m}" for m in memories) if memories else "- ఇంకా ప్రత్యేక జ్ఞాపకాలు లేవు."

    system_prompt = f"""
నీవు PHOENIX యాప్‌లోని అత్యంత ఇంటిలిజెంట్, శక్తివంతమైన AI బ్రెయిన్.
యూజర్ మాట్లాడే భాషకు తగ్గట్టుగా (ముఖ్యంగా సహజమైన తెలుగులో లేదా యూజర్ అడిగిన భాషలో) స్పష్టంగా, లోతుగా, ఆచరణాత్మకంగా సమాధానం ఇవ్వు.

[Long-Term Memory]
{memory_text}

[సందర్భం]
- సమయం: {current_time}
- యూజర్ మూడ్: {mood}

[నియమాలు]
1. యూజర్ ప్రశ్న, మూడ్, సందర్భాన్ని బట్టి స్పష్టమైన, ఉపయోగకరమైన సమాధానం ఇవ్వు.
2. Long-Term Memory లోని అంశాలను అవసరమైనప్పుడు మాత్రమే సహజంగా ఉపయోగించు.
3. తెలియని విషయాలను ఊహించి చెప్పకు; అస్పష్టంగా ఉంటే చిన్న, సూటి ప్రశ్న అడుగు.
""".strip()

    messages = [{"role": "system", "content": system_prompt}]
    for turn in history:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": user_text})

    reply = call_groq_api(
        messages=messages,
        model=REASONING_MODEL,
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


def handle_brain_request():
    user_text, user_id, mood, current_time = extract_incoming_data()
    if not user_text:
        return jsonify({
            "status": "error",
            "reply": "దయచేసి ఏదైనా మెసేజ్ పంపండి.",
            "response": "దయచేసి ఏదైనా మెసేజ్ పంపండి.",
            "answer": "దయచేసి ఏదైనా మెసేజ్ పంపండి.",
        }), 400

    try:
        reply = run_ai_brain(
            user_id=user_id,
            user_text=user_text,
            mood=mood,
            current_time=current_time,
        )
        return jsonify({
            "status": "success",
            "reply": reply,
            "response": reply,
            "answer": reply,
        }), 200
    except Exception as exc:
        err_msg = f"Phoenix AI Error: {str(exc)}"
        return jsonify({
            "status": "error",
            "reply": err_msg,
            "response": err_msg,
            "answer": err_msg,
            "error": str(exc),
        }), 500


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        return handle_brain_request()
    return jsonify({
        "status": "live",
        "app": "PHOENIX AI Brain",
        "groq_key_set": bool(GROQ_API_KEY),
        "reasoning_model": REASONING_MODEL,
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
