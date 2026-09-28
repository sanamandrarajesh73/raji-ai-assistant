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


PHOENIX_INSTRUCTIONS = """
You are PHOENIX AI. Creator: Rajesh.
(నీ పాత instructions అన్నీ ఇక్కడ అలాగే ఉంచు — అవి బాగున్నాయి)
"""


def ask_gemini(user_message: str) -> str:
    """Retry logic tho robust Gemini call."""
    if gemini_client is None:
        return "GEMINI_API_KEY set avvaledu. Server env lo key pettu."

    last_error = None
    for attempt in range(3):  # 3 retries
        try:
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=PHOENIX_INSTRUCTIONS,
                    temperature=0.7,
                    max_output_tokens=2048,
                ),
            )
            if response and response.text:
                return response.text.strip()
            return "Sorry, empty response vachindi. Malli try cheyyi."

        except Exception as e:
            last_error = str(e)
            wait = 2 ** attempt  # 1s, 2s, 4s backoff
            print(f"Attempt {attempt + 1} failed: {last_error}, retrying in {wait}s")
            time.sleep(wait)

    return f"Server busy / API error. Konchem tarvata try cheyyi. (Details: {last_error})"


@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "Phoenix AI Brain V1 running"})


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(silent=True)
        if not data or "message" not in data:
            return jsonify({"reply": "Message ledhu. JSON body lo 'message' field pampu."}), 400

        user_message = str(data["message"]).strip()
        if not user_message:
            return jsonify({"reply": "Khali message pampavu."}), 400

        reply = ask_gemini(user_message)
        return jsonify({"reply": reply})

    except Exception as e:
        print("Chat endpoint error:", e)
        return jsonify({"reply": "Internal error, malli try cheyyi."}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
