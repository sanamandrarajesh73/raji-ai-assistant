import os
import time

from flask import Flask, request, jsonify
from flask_cors import CORS

from google import genai
from google.genai import types

app = Flask(__name__)
CORS(app)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Default model ని 'gemini-2.5-flash' గా ఉంచాము (ఇది చాలా వేగంగా రెస్పాన్స్ ఇస్తుంది)
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
(మీ పాత ఇన్‌స్ట్రక్షన్స్‌ని ఇక్కడ యధాతథంగా ఉంచండి)
"""

def ask_gemini(user_message: str) -> str:
    """Retry logic తో కూడిన Gemini కాల్."""
    if gemini_client is None:
        return "Error: GEMINI_API_KEY సెట్ అవ్వలేదు. Render dashboard లో Environment Variable పెట్టండి."

    last_error = None
    for attempt in range(3):  # 3 సార్లు ట్రై చేస్తుంది
        try:
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=PHOENIX_INSTRUCTIONS,
                    temperature=0.7,
                    max_output_tokens=1024, # టైమౌట్ కాకుండా ఉండటానికి టోకెన్స్ కొద్దిగా తగ్గించాము
                ),
            )
            if response and response.text:
                return response.text.strip()
            
        except Exception as e:
            last_error = str(e)
            print(f"Attempt {attempt + 1} failed: {last_error}")
            time.sleep(1)  # మళ్లీ ట్రై చేయడానికి ముందు 1 సెకన్ ఆగుతుంది
            
    # 3 సార్లు ఫెయిల్ అయితే ఈ ఎర్రర్ రిటర్న్ అవుతుంది
    return f"Sorry, Gemini API కనెక్ట్ అవ్వడంలో సమస్య వచ్చింది. Error: {last_error}"


# మీ URL పనిచేయడానికి '/run' రూట్ (Route)
@app.route('/run', methods=['GET', 'POST'])
def run_query():
    # GET రిక్వెస్ట్ ఐతే URL నుండి, POST ఐతే JSON నుండి query ని తీసుకుంటుంది
    query = request.args.get('query') or request.json.get('query', '')
    
    if not query:
        return jsonify({"error": "Query parameter missing"}), 400
        
    reply = ask_gemini(query)
    return jsonify({"response": reply})

# లోకల్‌గా టెస్ట్ చేసుకోవడానికి
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    
