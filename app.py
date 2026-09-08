import os
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# Render Environment Variable నుండి GEMINI_API_KEY తీసుకోవడం
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Phoenix AI Super Brain కన్ఫిగరేషన్
system_instructions = (
    "యు ఆర్ ఫీనిక్స్ AI (Phoenix AI) - ఆల్ రౌండర్ రక్షకుడు & సహాయకుడు. "
    "Created by Rajesh. You possess complete knowledge from A to Z including Study Skills, "
    "Science, Mathematics, Coding, History, General Knowledge, and Live Updates. "
    "Always provide deep, comprehensive, clear, accurate, and structured answers in fluent Telugu. "
    "Use bullet points and clear formatting where helpful."
)

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=system_instructions
)

@app.route('/', methods=['GET'])
def health_check():
    return "🦅 Phoenix AI Super Backend is Active & Ready!", 200

@app.route('/run', methods=['GET', 'POST'])
def run_ai():
    # 1. URL Parameter (GET) లేదా JSON / Form (POST) నుండి query గ్రహించడం
    user_query = request.args.get('query', '').strip()
    
    if not user_query and request.is_json:
        data = request.get_json(silent=True) or {}
        user_query = data.get('prompt') or data.get('query', '')
        
    if not user_query and request.form:
        user_query = request.form.get('prompt') or request.form.get('query', '')

    if not user_query:
        user_query = request.get_data(as_text=True).strip()

    # 2. ప్రశ్నేదీ లేకపోతే డిఫాల్ట్ రెస్పాన్స్
    if not user_query:
        return jsonify({
            "status": "success",
            "title": "🦅 PHOENIX AI",
            "data": "నమస్తే రాజేష్! దయచేసి చదువు, సైన్స్, కోడింగ్ లేదా ఏ లోకజ్ఞానం గురించైనా అడగండి."
        })

    # 3. API Key చెకింగ్
    if not GEMINI_API_KEY:
        return jsonify({
            "status": "error",
            "title": "⚠️ PHOENIX CONFIG ERROR",
            "data": "Render దాంట్లో GEMINI_API_KEY సెట్ చేయలేదు! దయచేసి ఎన్విరాన్మెంట్ వేరియబుల్ ఇవ్వండి."
        })

    try:
        # 4. Gemini AI ఇంజిన్ ద్వారా డైనమిక్ సమాధానం జనరేట్ చేయడం
        response = model.generate_content(user_query)
        ai_response = response.text if response and response.text else "సమాచారం ప్రాసెస్ చేయడంలో చిన్న సమస్య వచ్చింది."

        # Markdown సింబల్స్ క్లీన్ చేయాలనుకుంటే (ఆప్షనల్)
        clean_response = ai_response.replace('**', '').replace('###', '').strip()

        return jsonify({
            "status": "success",
            "title": "🦅 PHOENIX AI",
            "data": clean_response
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "title": "🚨 PHOENIX AI ERROR",
            "data": f"AI సర్వర్ ప్రాసెసింగ్ లోపం: {str(e)}"
        })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    app.run(host='0.0.0.0', port=port)
