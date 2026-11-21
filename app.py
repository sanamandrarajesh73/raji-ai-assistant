import os
import json
import sqlite3
import threading
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# అత్యుత్తమ రీజనింగ్ & తెలుగు/సందర్భ అవగాహన కోసం
REASONING_MODEL = os.environ.get("GROQ_REASONING_MODEL", "llama-3.3-70b-versatile")
# వేగంగా, కచ్చితంగా నిజాలు తీయడానికి
EXTRACTOR_MODEL = os.environ.get("GROQ_EXTRACTOR_MODEL", "llama-3.1-8b-instant")

DB_PATH = os.environ.get("BRAIN_DB_PATH", "phoenix_brain.db")
DB_LOCK = threading.Lock()


def init_db():
    with DB_LOCK:
        conn = sqlite3.connect(DB_PATH)
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


def groq_chat(messages, model, temperature=0.5, max_tokens=600, response_json=False):
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
    if response_json:
        payload["response_format"] = {"type": "json_object"}

    resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=35)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def fetch_short_term_memory(user_id, limit=8):
    with DB_LOCK:
        conn = sqlite3.connect(DB_PATH)
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


def save_chat_turn(user_id, role, content, mood="neutral"):
    now = datetime.utcnow().isoformat()
    with DB_LOCK:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO chat_history (user_id, role, content, mood, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, role, content, mood, now),
        )
        conn.commit()
        conn.close()


def fetch_long_term_memory(user_id, query="", limit=12):
    with DB_LOCK:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT category, fact FROM user_memories
            WHERE user_id = ?
            ORDER BY id DESC LIMIT 50
            """,
            (user_id,),
        )
        rows = cur.fetchall()
        conn.close()

    if not rows:
        return []

    # ప్రస్తుత ప్రశ్నకు సంబంధించిన కీవర్డ్స్ ఉన్న జ్ఞాపకాలకు ప్రాధాన్యత
    query_words = {w.lower() for w in query.split() if len(w) > 2}
    scored = []
    for idx, (cat, fact) in enumerate(rows):
        fact_words = {w.lower() for w in fact.split() if len(w) > 2}
        overlap = len(query_words & fact_words)
        # ఇటీవలి వాటికి స్వల్ప బోనస్ + కీవర్డ్ మ్యాచ్ స్కోర్
        score = overlap * 10 + max(0, 20 - idx)
        scored.append((score, cat, fact))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [f"[{cat}] {fact}" for _, cat, fact in scored[:limit]]


def save_facts_to_memory(user_id, items):
    now = datetime.utcnow().isoformat()
    with DB_LOCK:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        for item in items:
            fact = item.get("fact", "").strip() if isinstance(item, dict) else str(item).strip()
            category = item.get("category", "general").strip() if isinstance(item, dict) else "general"
            if fact:
                cur.execute(
                    """
                    INSERT OR IGNORE INTO user_memories (user_id, category, fact, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, category, fact, now),
                )
        conn.commit()
        conn.close()


def extract_and_save_new_facts(user_id, user_text, assistant_response):
    try:
        system_msg = """
        మీరు ఒక Intelligent Memory Extractor.
        యూజర్ సంభాషణ నుండి భవిష్యత్తులో గుర్తుంచుకోవాల్సిన స్థిరమైన, ముఖ్యమైన విషయాలు మాత్రమే తీయండి:
        - preferences (ఇష్టాలు/అభిప్రాయాలు)
        - goals / projects (లక్ష్యాలు / ప్రాజెక్టులు)
        - habits / routines (అలవాట్లు / దినచర్య)
        - key_facts (ముఖ్యమైన వ్యక్తిగత లేదా సాంకేతిక వివరాలు)

        తాత్కాలిక మాటలు ("hi", "ok", "thanks") లేదా ఊహాజనిత విషయాలు సేవ్ చేయవద్దు.
        JSON ఆబ్జెక్ట్ మాత్రమే ఇవ్వండి:
        {"memories": [{"category": "preference|goal|habit|key_fact", "fact": "స్పష్టమైన చిన్న వాక్యం"}]}
        ఏమీ లేకపోతే {"memories": []} అని ఇవ్వండి.
        """
        content = f"User: {user_text}\nAssistant: {assistant_response}"
        raw = groq_chat(
            messages=[
                {"role": "system", "content": system_msg.strip()},
                {"role": "user", "content": content},
            ],
            model=EXTRACTOR_MODEL,
            temperature=0.1,
            max_tokens=250,
            response_json=True,
        )
        parsed = json.loads(raw)
        memories = parsed.get("memories", [])
        if isinstance(memories, list) and memories:
            save_facts_to_memory(user_id, memories)
    except Exception as e:
        print(f"[Memory Extraction Error]: {e}")


def call_llm(system_instruction, chat_history, user_message):
    messages = [{"role": "system", "content": system_instruction}]
    for turn in chat_history:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": user_message})

    return groq_chat(
        messages=messages,
        model=REASONING_MODEL,
        temperature=0.55,
        max_tokens=600,
    )


def process_user_input(user_id, user_text, voice_emotion="neutral", current_time=None):
    if not current_time:
        current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    memories = fetch_long_term_memory(user_id, query=user_text)
    recent_chat = fetch_short_term_memory(user_id, limit=8)

    memory_block = "\n".join(f"- {m}" for m in memories) if memories else "- ఇంకా ప్రత్యేక జ్ఞాపకాలు సేవ్ కాలేదు."

    brain_prompt = f"""
    నీవు PHOENIX యాప్‌లోని అత్యంత ఇంటిలిజెంట్, శక్తివంతమైన వ్యక్తిగత AI బ్రెయిన్.
    యూజర్ మాట్లాడే భాషకు తగ్గట్టుగా (ముఖ్యంగా సహజమైన తెలుగులో లేదా యూజర్ అడిగిన భాషలో) స్పష్టంగా, లోతుగా, ఆచరణాత్మకంగా సమాధానం ఇవ్వు.

    [యూజర్ గురించి తెలిసిన Long-Term Memory]
    {memory_block}

    [ప్రస్తుత సందర్భం]
    - సమయం: {current_time}
    - యూజర్ మానసిక స్థితి / గొంతు భావం (Mood/Emotion): {voice_emotion}

    [ఇంటిలిజెంట్ బిహేవియర్ నియమాలు]
    1. యూజర్ మూడ్ ({voice_emotion}) మరియు సందర్భాన్ని అర్థం చేసుకుని దానికి తగ్గ టోన్‌లో స్పందించు (అలసటగా ఉంటే సానుభూతి + తేలికైన పరిష్కారం, టెక్నికల్‌గా అడిగితే కచ్చితమైన ఇంజనీరింగ్ స్పష్టత).
    2. Long-Term Memory లోని విషయాలను బలవంతంగా ప్రతిసారి వాడకు; ప్రస్తుత ప్రశ్నకు/సందర్భానికి నిజంగా ఉపయోగపడేటప్పుడే సహజంగా జత చేయి.
    3. సమాధానం సాధారణ AI లా కాకుండా ఆలోచించి, విశ్లేషించి ఇచ్చినట్లు స్పష్టంగా, నిర్మాణాత్మకంగా ఉండాలి.
    4. తెలియని విషయాలను కల్పించి చెప్పకు; అస్పష్టంగా ఉంటే చిన్న, సూటి ప్రశ్న అడుగు.
    """.strip()

    response = call_llm(
        system_instruction=brain_prompt,
        chat_history=recent_chat,
        user_message=user_text,
    )

    save_chat_turn(user_id, "user", user_text, mood=voice_emotion)
    save_chat_turn(user_id, "assistant", response, mood="helpful")

    threading.Thread(
        target=extract_and_save_new_facts,
        args=(user_id, user_text, response),
        daemon=True,
    ).start()

    return response


@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "PHOENIX AI Brain",
        "groq_configured": bool(GROQ_API_KEY),
        "reasoning_model": REASONING_MODEL,
    })


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    # వేర్వేరు ఫ్రంట్‌ఎండ్ ఫీల్డ్ పేర్లకు సపోర్ట్
    user_text = (data.get("message") or data.get("prompt") or data.get("text") or "").strip()
    if not user_text:
        return jsonify({"error": "message is required", "reply": "దయచేసి ఏదైనా మెసేజ్ లేదా ప్రశ్న పంపండి."}), 400

    user_id = str(data.get("user_id") or data.get("userId") or "default_user")
    voice_emotion = str(data.get("voice_emotion") or data.get("mood") or "neutral")
    current_time = data.get("current_time") or data.get("time")

    try:
        reply = process_user_input(
            user_id=user_id,
            user_text=user_text,
            voice_emotion=voice_emotion,
            current_time=current_time,
        )
        return jsonify({
            "reply": reply,
            "response": reply,
            "status": "success",
        })
    except RuntimeError as e:
        return jsonify({
            "error": str(e),
            "reply": f"Phoenix AI Error: {str(e)}",
        }), 500
    except requests.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else 502
        detail = e.response.text[:300] if e.response is not None else str(e)
        return jsonify({
            "error": f"Groq API HTTP {status_code}: {detail}",
            "reply": f"Groq API లో సమస్య వచ్చింది (HTTP {status_code}). Model ID లేదా API Key చెక్ చేయండి.",
        }), 502
    except Exception as e:
        return jsonify({
            "error": str(e),
            "reply": f"Phoenix AI Brain Error: {str(e)}",
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
