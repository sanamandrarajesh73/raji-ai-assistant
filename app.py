import os
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

API_KEY = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6Jhv4mySPiVKaDCiJVRnKNKh-RZzvKqHDydvjdMy6-tqw")
genai.configure(api_key=API_KEY)

SYSTEM_PROMPT = """
You are Phoenix Next-Gen AI — The Ultimate Academic and Vocational Engine.

RULES:
- Always respond in simple Telugu mixed with standard English terms.
- Use ONLY clean Bullet Points or numbered lists.
- NO Markdown characters: hashes (#), asterisks (*), or pipes (|).
- FOR DIAGRAMS/DRAWINGS: Provide a step-by-step Pen & Paper drawing guide, followed by an HD diagram link:
  "HD Diagram చూడటానికి ఇక్కడ క్లిక్ చేయండి: https://www.google.com/search?tbm=isch&q=[SEARCH_TERM_IN_ENGLISH]"
"""

model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=SYSTEM_PROMPT
)

@app.route("/", methods=["GET"])
def home():
    return "Phoenix AI Engine Active!", 200

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(silent=True) or {}
        user_message = data.get("message", "").strip()

        # Input fallback logic
        if not user_message:
            user_message = request.form.get("message", "").strip()

        if not user_message:
            return "దయచేసి మీ ప్రశ్నను వివరంగా టైప్ చేయండి.", 200, {'Content-Type': 'text/plain; charset=utf-8'}

        response = model.generate_content(user_message)
        raw_text = response.text or "సమాధానం దొరకలేదు."

        clean_text = raw_text.replace("*", "").replace("#", "").replace("|", "").strip()
        return clean_text, 200, {'Content-Type': 'text/plain; charset=utf-8'}

    except Exception as e:
        print(f"Error: {e}")
        return f"సాంకేతిక లోపం వచ్చింది: {str(e)}", 200, {'Content-Type': 'text/plain; charset=utf-8'}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
