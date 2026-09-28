import os
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types

app = Flask(__name__)
CORS(app)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

gemini_client = None
if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        print("Gemini client ready")
    except Exception as e:
        print("Gemini client error:", e)

PHOENIX_INSTRUCTIONS = "You are PHOENIX AI. Creator: Rajesh."

def ask_gemini(user_message: str) -> str:
    if gemini_client is None:
        return "Error: GEMINI_API_KEY set avvaledu."

    last_error = None
    for attempt in range(3):
        try:
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=PHOENIX_INSTRUCTIONS,
                    temperature=0.7,
                    max_output_tokens=1024,
                ),
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            last_error = str(e)
            print(f"Attempt {attempt + 1} failed: {last_error}")
            time.sleep(1)
            
    return f"Sorry, error vachindi: {last_error}"

@app.route('/run', methods=['GET', 'POST'])
def run_query():
    query = request.args.get('query') or request.json.get('query', '') if request.is_json else request.args.get('query', '')
    if not query:
        return jsonify({"error": "Query parameter missing"}), 400
    reply = ask_gemini(query)
    return jsonify({"response": reply})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
# హోమ్ పేజీ కోసం రూట్ (యాప్ నడుస్తుందో లేదో తెలుసుకోవడానికి)
@app.route('/', methods=['GET'])
def home():
    return "Phoenix AI Backend is Running Successfully!"
