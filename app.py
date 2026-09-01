import os
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# Setting your exact Gemini API Key safely
API_KEY = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6Jhv4mySPiVKaDCiJVRnKNKh-RZzvKqHDydvjdMy6-tqw")
genai.configure(api_key=API_KEY)

# Universal System Instructions
SYSTEM_PROMPT = """
You are Phoenix Next-Gen AI — The Ultimate Academic, Career, and Real-Time Search Intelligence Engine.

DOMAINS:
1. Academic: Maths, Physics, Chemistry, Biology, History, Civics, Economics, Computer Science, Law, Pharmacy, Literature.
2. Professional & Vocational: B.Sc Nursing, Electrician, Software Development, Banking Exams, Diploma, Trade Courses.

STRICT FORMATTING RULES:
- Always respond in simple, clean Telugu mixed with standard English terms.
- Use strictly ONLY Bullet Points and simple numbered lists.
- ABSOLUTELY NO Markdown symbols: do not use hashes (#), asterisks (*), or pipes (|).
- Never draw ASCII art boxes or text-based diagrams as they break mobile screens.
- FOR DIAGRAMS/DRAWINGS: Provide a step-by-step Pen & Paper drawing guide, followed by an HD diagram link:
  "HD Diagram చూడటానికి ఇక్కడ క్లిక్ చేయండి: https://www.google.com/search?tbm=isch&q=[SEARCH_TERM_IN_ENGLISH]"
"""

# Initialize Gemini 2.5 Flash Model safely
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=SYSTEM_PROMPT
)

@app.route("/", methods=["GET"])
def home():
    return "Phoenix AI - 100% Quality Production Engine Active!", 200

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(silent=True) or {}
        user_message = data.get("message", "").strip()

        if not user_message:
            return "దయచేసి ఏదైనా ప్రశ్న లేదా డౌట్ అడగండి.", 200, {'Content-Type': 'text/plain; charset=utf-8'}

        # Generating AI response
        response = model.generate_content(user_message)
        raw_text = response.text or "క్షమించండి, సమాధానం దొరకలేదు."

        # Cleaning broken markdown symbols for mobile UI and TTS readability
        clean_text = raw_text.replace("*", "").replace("#", "").replace("|", "").strip()

        return clean_text, 200, {'Content-Type': 'text/plain; charset=utf-8'}

    except Exception as e:
        print(f"Server Error: {e}")
        return f"సాంకేతిక లోపం వచ్చింది: {str(e)}", 200, {'Content-Type': 'text/plain; charset=utf-8'}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
