# -*- coding: utf-8 -*-
import os
import time
import requests
from flask import Flask, request

app = Flask(__name__)

GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
GROQ_KEY = os.environ.get("GROQ_API_KEY", "")  # ఆప్షనల్ - బ్యాకప్

# --- Gemini latest models chain (2.0/2.5 dead/blocked) ---
MODELS = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"]

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent?key={}"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """యు ఆర్ ఫీనిక్స్ AI (Phoenix AI) — ఆల్ రౌండర్ రక్షకుడు & సహాయకుడు.
నువ్వు అన్ని విషయాల్లో నిపుణుడివి: చదువులు, ఆరోగ్యం, స్టాక్ మార్కెట్, బంగారం ధరలు,
క్రికెట్, వ్యవసాయం, ప్రభుత్వ పథకాలు, టెక్నాలజీ, కెరీర్ గైడెన్స్.
నియమాలు:
1. సమాధానాలు స్పష్టంగా, సింపుల్ తెలుగులో + ఇంగ్లీష్ టెర్మ్స్ కలిపి ఇవ్వు.
2. నెంబర్డ్ లిస్ట్స్ లేదా బుల్లెట్ పాయింట్స్ వాడు.
3. Markdown గుర్తులు (#, *, |) అస్సలు వాడకు — మొబైల్ స్క్రీన్ పగిలిపోతుంది.
4. డ్రాయింగ్/డయాగ్రమ్ అడిగితే: Step 1, Step 2, Step 3 గా కలం-కాగితం గైడ్ ఇవ్వు,
   చివర్లో: "HD Diagram: https://www.google.com/search?tbm=isch&q=SEARCH_TERM"
5. లైవ్ సమాచారం (ధరలు, వార్తలు, స్కోర్లు) అడిగితే అత్యంత తాజా సమాచారం ఇవ్వు,
   తెలియకపోతే "ఇది నా నాలెడ్జ్ లిమిట్ - లేటెస్ట్ చెక్ చెయ్యి" అని నిజాయితీగా చెప్పు.
6. ఎప్పుడూ స్నేహపూర్వకంగా, ఉత్సాహంగా మాట్లాడు!"""

# --- Layer 1+2: Gemini with Google Search grounding ---
def ask_gemini(question):
    payload = {
        "contents": [{"parts": [{"text": SYSTEM_PROMPT + "\n\nప్రశ్న: " + question}]}],
        "tools": [{"google_search": {}}]  # లైవ్ ఇన్ఫర్మేషన్!
    }
    last_err = ""
    for model in MODELS:
        try:
            r = requests.post(GEMINI_URL.format(model, GEMINI_KEY),
                              json=payload,
                              headers={"Content-Type": "application/json"},
                              timeout=40)
            if r.status_code == 200:
                data = r.json()
                parts = data["candidates"][0]["content"]["parts"]
                text = ""
                for p in parts:
                    if "text" in p:
                        text += p["text"]
                if text.strip():
                    return clean(text)
        except requests.exceptions.Timeout:
            last_err = "timeout"
        except Exception as e:
            last_err = str(e)
    return None

# --- Layer 3: Groq backup (free, fast) ---
def ask_groq(question):
    if not GROQ_KEY:
        return None
    try:
        r = requests.post(GROQ_URL,
            json={"model": "llama-3.3-70b-versatile",
                  "messages": [{"role": "user",
                      "content": SYSTEM_PROMPT + "\n\nప్రశ్న: " + question}]},
            headers={"Authorization": "Bearer " + GROQ_KEY},
            timeout=30)
        if r.status_code == 200:
            return clean(r.json()["choices"][0]["message"]["content"])
    except Exception:
        pass
    return None

def clean(text):
    return (text.replace("**", "").replace("*", "")
                .replace("#", "").replace("|", "").strip())

def ask_all(question):
    # Layer 1+2: Gemini (with search grounding)
    ans = ask_gemini(question)
    if ans:
        return ans
    # Layer 3: Groq backup
    ans = ask_groq(question)
    if ans:
        return ans
    return ("క్షమించండి నేస్తమా! సర్వర్లన్నీ బిజీగా ఉన్నాయి. "
            "కొంచెం తర్వాత మళ్ళీ ప్రయత్నించు 🙏")

@app.route("/", methods=["GET", "POST"])
def home():
    # GET: యాప్ + బ్రౌజర్ రెండూ పని చేస్తాయి
    if request.method == "GET":
        q = request.args.get("q", "").strip()
        if not q:
            return "Phoenix AI v11.0 Active! ప్రశ్న: /?q=మీ_ప్రశ్న"
        return ask_all(q), 200, {"Content-Type": "text/plain; charset=utf-8"}
    # POST: JSON / form / raw — అన్నీ సపోర్ట్
    data = request.get_json(silent=True) or {}
    q = data.get("prompt") or data.get("message") or request.form.get("prompt") \
        or request.get_data(as_text=True)
    if not q or not q.strip():
        return "దయచేసి ప్రశ్న టైప్ చేయండి.", 200
    return ask_all(q.strip()), 200, {"Content-Type": "text/plain; charset=utf-8"}

@app.route("/health")
def health():
    return "Phoenix OK v11.0 MAX POWER"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
PYEOF
