import os
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=(
        "యు ఆర్ ఫీనిక్స్ AI (Phoenix AI) - ఆల్ రౌండర్ రక్షకుడు & సహాయకుడు. "
        "Created by Rajesh. Always provide deep, comprehensive, and accurate answers in fluent Telugu."
    )
)

@app.route('/', methods=['GET'])
def home():
    return "🦅 Phoenix AI Backend is Active!", 200

@app.route('/run', methods=['GET', 'POST'])
def run_ai():
    user_query = request.args.get('query', '').strip()
    
    if not user_query and request.is_json:
        data = request.get_json(silent=True) or {}
        user_query = data.get('prompt') or data.get('query', '')

    if not user_query:
        return jsonify({"status": "success", "title": "🦅 PHOENIX AI", "data": "నమస్తే రాజేష్! దయచేసి ఏదైనా అడగండి."})

    try:
        response = model.generate_content(user_query)
        clean_text = response.text.replace('**', '').replace('###', '').strip()
        return jsonify({"status": "success", "title": "🦅 PHOENIX AI", "data": clean_text})
    except Exception as e:
        return jsonify({"status": "error", "title": "🦅 PHOENIX AI ERROR", "data": f"సమస్య: {str(e)}"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    app.run(host='0.0.0.0', port=port)
        
