import os
import json
import threading
import requests

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# మీ Groq Console లో అందుబాటులో ఉన్న మోడల్ ID లను ఇక్కడ సెట్ చేయండి
REASONING_MODEL = os.environ.get("GROQ_REASONING_MODEL", "llama-3.3-70b-versatile")
EXTRACTOR_MODEL = os.environ.get("GROQ_EXTRACTOR_MODEL", "llama-3.1-8b-instant")


def groq_chat(messages, model, temperature=0.5, max_tokens=500, response_json=False):
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY environment variable is missing.")

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

    resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def call_llm(system_instruction, chat_history, user_message):
    messages = [{"role": "system", "content": system_instruction}]
    for turn in chat_history[-8:]:
        if turn.get("role") in ("user", "assistant") and turn.get("content"):
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": user_message})

    return groq_chat(
        messages=messages,
        model=REASONING_MODEL,
        temperature=0.55,
        max_tokens=500,
    )


def extract_and_save_new_facts(user_id, user_text, assistant_response):
    prompt = """
    ఈ సంభాషణ నుండి యూజర్ గురించి భవిష్యత్తులో గుర్తుంచుకోవాల్సిన ముఖ్యమైన, స్థిరమైన నిజాలు (preferences, habits, goals, projects, key facts) ఉంటే మాత్రమే తీయండి.
    తాత్కాలిక మూడ్ లేదా పనికిరాని మాటలను సేవ్ చేయవద్దు.
    JSON రూపంలో మాత్రమే ఇలా ఇవ్వండి:
    {"facts": ["నిజం 1", "నిజం 2"]}
    ఏమీ లేకపోతే {"facts": []} అని ఇవ్వండి.
    """
    content = f"User: {user_text}\nAssistant: {assistant_response}"
    raw = groq_chat(
        messages=[
            {"role": "system", "content": prompt.strip()},
            {"role": "user", "content": content},
        ],
        model=EXTRACTOR_MODEL,
        temperature=0.1,
        max_tokens=200,
        response_json=True,
    )

    try:
        parsed = json.loads(raw)
        facts = [f.strip() for f in parsed.get("facts", []) if isinstance(f, str) and f.strip()]
    except Exception:
        facts = []

    if facts:
        save_facts_to_memory(user_id, facts)  # మీ DB / Vector store ఫంక్షన్


def process_user_input(user_id, user_text, voice_emotion="neutral", current_time="night"):
    user_profile = fetch_long_term_memory(user_id, query=user_text)
    recent_chat = fetch_short_term_memory(user_id)

    brain_prompt = f"""
    నీవు యూజర్‌ను లోతుగా అర్థం చేసుకునే అత్యంత శక్తివంతమైన వ్యక్తిగత AI బ్రెయిన్.
    - యూజర్ గురించి తెలిసిన నిజాలు (Memory): {user_profile}
    - ప్రస్తుత సమయం: {current_time}
    - యూజర్ మానసిక స్థితి / గొంతు భావం: {voice_emotion}

    నియమాలు:
    1. యూజర్ ప్రస్తుత భావోద్వేగం, సమయం, మరియు సందర్భానికి తగ్గట్టుగా సహజంగా, స్పష్టంగా, సానుభూతితో మాట్లాడు.
    2. పాత జ్ఞాపకాలను బలవంతంగా కాకుండా, ప్రస్తుత ప్రశ్నకు/సందర్భానికి నిజంగా సంబంధించినప్పుడు మాత్రమే సహజంగా వాడు.
    3. తెలియని విషయాలను ఊహించి నిజంలా చెప్పకు; స్పష్టత అవసరమైతే చిన్న, సూటి ప్రశ్న అడుగు.
    4. సమాధానం ఆచరణాత్మకంగా, స్పష్టంగా ఉండాలి.
    """.strip()

    response = call_llm(
        system_instruction=brain_prompt,
        chat_history=recent_chat,
        user_message=user_text,
    )

    # రిప్లై ఆలస్యం కాకుండా బ్యాక్‌గ్రౌండ్‌లో మెమరీ అప్‌డేట్
    threading.Thread(
        target=extract_and_save_new_facts,
        args=(user_id, user_text, response),
        daemon=True,
    ).start()

    return response
