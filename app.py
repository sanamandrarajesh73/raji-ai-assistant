import os
import re
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Primary & Secondary API Models
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
PRIMARY_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
FALLBACK_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={GEMINI_API_KEY}"

def clean_text(text):
    """మొబైల్ స్క్రీన్‌పై నీట్‌గా కనిపిస్తూ Markdown లేని క్లీన్ టెక్స్ట్ తయారు చేస్తుంది"""
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'#+', '', text)
    text = re.sub(r'`+', '', text)
    return text.strip()

@app.route('/', methods=['GET'])
def home():
    return "Phoenix AI Engine is Live & Active!", 200

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json(silent=True) or {}
        user_message = data.get("message", "").strip()

        if not user_message:
            return jsonify({"response": "దయచేసి ఏదైనా ప్రశ్న అడగండి."}), 400

        # System Prompt for High-Intelligence Reasoning
        system_instruction = (
            "You are Phoenix AI, a ultra-high-performance AI assistant. "
            "Respond in clear, natural Telugu unless requested otherwise. "
            "Keep formatting extremely clean without markdown tags."
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{system_instruction}\n\nUser Question: {user_message}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1000
            }
        }

        # Self-Healing System: Trying Primary Engine
        try:
            res = requests.post(PRIMARY_URL, json=payload, timeout=18)
            if res.status_code == 200:
                raw_reply = res.json()['candidates'][0]['content']['parts'][0]['text']
                return jsonify({"response": clean_text(raw_reply)}), 200
        except Exception:
            pass # Auto-healing fallback trigger

        # Auto-Healing Fallback: Primary ఫెయిల్ అయితే వెంటనే సెకండరీ ఇంజిన్ యాక్టివేట్ అవుతుంది
        res_fallback = requests.post(FALLBACK_URL, json=payload, timeout=18)
        if res_fallback.status_code == 200:
            raw_reply = res_fallback.json()['candidates'][0]['content']['parts'][0]['text']
            return jsonify({"response": clean_text(raw_reply)}), 200

        return jsonify({"response": "Phoenix AI ప్రస్తుతం ప్రాసెస్ చేస్తోంది, దయచేసి ఒక క్షణం ఆగి మళ్లీ ప్రయత్నించండి."}), 500

    except Exception as e:
        return jsonify({"response": "సిస్టమ్ రీ-రౌట్ అవుతోంది. దయచేసి మళ్లీ టైప్ చేయండి."}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
