import os
import urllib.parse
from flask import Flask, request, jsonify
from google import genai
from google.genai import types

app = Flask(__name__)

# Fetch Gemini API Key from Render Environment Variables
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Ultimate System Prompt: Perplexity-Style Search + Student Drawing Guide + All Streams
SYSTEM_PROMPT = """
You are Phoenix Next-Gen AI — The Ultimate Universal Academic, Career, and Real-Time Search Intelligence Engine.

COVERED DOMAINS:
1. Academic Subjects: Maths, Physics, Chemistry, Biology, History, Civics, Economics, Computer Science, Law, Pharmacy, Literature, etc.
2. Professional & Vocational Streams: B.Sc Nursing, Electrician, Software Development, Banking Exams, Diploma, Trade Courses.

CORE FORMATTING RULES:
1. Always respond in simple, natural Telugu mixed with standard English terms.
2. Structure all answers using ONLY clean numbered lists or simple bullet points.
3. ABSOLUTELY NO Markdown characters: do NOT use hashes (#), asterisks (*), pipes (|), or ASCII art boxes. (These break mobile screen layouts).
4. REAL-TIME FACTS: Provide live, accurate, up-to-date facts when asked about current news, sports, or live data.
5. FOR DIAGRAMS/DRAWINGS (Nursing, Science, Engineering):
   - Provide a Step-by-Step Pen & Paper drawing guide (Step 1, Step 2, Step 3).
   - At the very end, generate an HD diagram search link like this:
     "HD Diagram చూడటానికి ఇక్కడ క్లిక్ చేయండి: https://www.google.com/search?tbm=isch&q=[SEARCH_TERM_IN_ENGLISH]"
"""

@app.route("/", methods=["GET"])
def home():
    return "Phoenix Next-Gen Engine Active!", 200

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(silent=True) or {}
        user_message = data.get("message", "").strip()

        if not user_message:
            return "దయచేసి ఏదైనా ప్రశ్న లేదా డౌట్ అడగండి.", 200, {'Content-Type': 'text/plain; charset=utf-8'}

        # Grounding with Google Search for Real-Time Facts
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"{SYSTEM_PROMPT}\n\nUser Question: {user_message}",
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )

        raw_text = response.text or "క్షమించండి, సమాధానం దొరకలేదు."

        # Remove markdown clutter to ensure clean output
        clean_text = raw_text.replace("*", "").replace("#", "").replace("|", "").strip()

        return clean_text, 200, {'Content-Type': 'text/plain; charset=utf-8'}

    except Exception as e:
        print(f"Server Error: {e}")
        return "క్షమించండి, సర్వర్‌లో చిన్న సాంకేతిక లోపం వచ్చింది. మళ్ళీ ప్రయత్నించండి.", 200, {'Content-Type': 'text/plain; charset=utf-8'}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
