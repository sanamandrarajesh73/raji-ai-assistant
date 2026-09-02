import os
import json
from flask import Flask, request
import google.generativeai as genai

app = Flask(__name__)

# Updated API Key provided by Rajesh
API_KEY = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6L73Pp34Q0AzbCBAgkkR2nPZ82zYfH37KSZ-hSx0p-R3g")
genai.configure(api_key=API_KEY)

# Universal System Instructions for Phoenix AI
SYSTEM_PROMPT = """
You are Phoenix Next-Gen AI — The Ultimate Academic, Career, and Real-Time Search Intelligence Engine.

DOMAINS:
1. Academic: Maths, Physics, Chemistry, Biology, History, Civics, Economics, Computer Science, Law, Pharmacy, Literature.
2. Professional & Vocational: B.Sc Nursing, Electrician, Software Development, Banking Exams, Diploma, Trade Courses.

STRICT FORMATTING RULES:
- Always respond in simple, clean Telugu mixed with standard English terms.
- Use strictly ONLY Bullet Points and simple numbered lists.
- ABSOLUTELY NO Markdown symbols: do not use hashes (#), asterisks (*), or pipes (|).
- Never draw ASCII art boxes or text-based diagrams.
- FOR DIAGRAMS/DRAWINGS: Provide a step-by-step Pen & Paper drawing guide, followed by an HD diagram link:
  "HD Diagram చూడటానికి ఇక్కడ క్లిక్ చేయండి: https://www.google.com/search?tbm=isch&q=[SEARCH_TERM_IN_ENGLISH]"
"""

# Initialize Gemini Model
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=SYSTEM_PROMPT
)

@app.route("/", methods=["GET"])
def home():
    return "Phoenix AI Engine 100% Active & Ready!", 200

@app.route("/chat", methods=["POST"])
def chat():
    try:
        # App Inventor నుండి వచ్చే డేటాను ఫ్లెక్సిబుల్‌గా హ్యాండిల్ చేయడం
        raw_data = request.get_data(as_text=True) or ""
        user_message = ""

        # JSON Parse ప్రయత్నం
        try:
            data = request.get_json(silent=True) or json.loads(raw_data)
            if isinstance(data, dict):
                user_message = data.get("message", "")
        except Exception:
            pass

        # ఒకవేళ JSON బ్రేక్ అయితే రా టెక్స్ట్ నుండి క్లీన్ చేయడం
        if not user_message and raw_data:
            user_message = raw_data.replace('{"message":"', '').replace('"}', '').replace('"', '').strip()

        # మెసేజ్ ఖాళీగా ఉంటే హెచ్చరిక
        if not user_message:
            return "దయచేసి మీ ప్రశ్నను వివరంగా టైప్ చేయండి.", 200, {'Content-Type': 'text/plain; charset=utf-8'}

        # AI రెస్పాన్స్ జనరేట్ చేయడం
        response = model.generate_content(user_message)
        raw_text = response.text or "సమాధానం దొరకలేదు."

        # మొబైల్ యూజర్ ఇంటర్‌ఫేస్ కోసం మార్క్‌డౌన్ చిహ్నాలను తొలగించడం
        clean_text = raw_text.replace("*", "").replace("#", "").replace("|", "").strip()

        return clean_text, 200, {'Content-Type': 'text/plain; charset=utf-8'}

    except Exception as e:
        print(f"Server Error: {e}")
        return f"సాంకేతిక లోపం వచ్చింది: {str(e)}", 200, {'Content-Type': 'text/plain; charset=utf-8'}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
