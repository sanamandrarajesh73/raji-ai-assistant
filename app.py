import os
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# Fetch Gemini API Key from Render Environment Variables
API_KEY = os.environ.get("GEMINI_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)

# Priority list of models to try for maximum reliability
MODELS_TO_TRY = [
    'gemini-1.5-flash',
    'gemini-1.5-pro',
    'gemini-pro'
]

def generate_ai_response(prompt_text):
    if not API_KEY:
        return "సాంకేతిక లోపం: API Key కాన్ఫిగర్ చేయబడలేదు. దయచేసి Render లో GEMINI_API_KEY సెట్ చేయండి."

    # Try available models in order
    for model_name in MODELS_TO_TRY:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt_text)
            if response and response.text:
                return response.text
        except Exception as e:
            continue  # Try next model if current model fails

    # Fallback response if all configured models encounter errors
    return "సాంకేతిక లోపం: AI సర్వీస్ ప్రస్తుతం అందుబాటులో లేదు. దయచేసి కొద్దిసేపటి తర్వాత మళ్లీ ప్రయత్నించండి."

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'GET':
        return "Phoenix AI Backend is Active and Running!"

    try:
        data = request.get_json(silent=True)
        user_prompt = None

        if data and 'prompt' in data:
            user_prompt = data['prompt']
        elif request.form and 'prompt' in request.form:
            user_prompt = request.form['prompt']
        else:
            raw_text = request.get_data(as_text=True)
            if raw_text:
                user_prompt = raw_text

        if not user_prompt:
            return "దయచేసి ఏదైనా ప్రశ్న లేదా సందేశం టైప్ చేయండి.", 400

        # System Persona for Phoenix AI Assistant
        system_context = (
            "యు ఆర్ ఫీనిక్స్ AI (Phoenix AI) - ఆల్ రౌండర్ రక్షకుడు & సహాయకుడు. "
            "సమాధానాలు స్పష్టంగా, సులువుగా అర్థమయ్యేలా తెలుగు భాషలో అందించు.\n\n"
            f"యూజర్ ప్రశ్న: {user_prompt}"
        )

        ai_response = generate_ai_response(system_context)
        return ai_response, 200, {'Content-Type': 'text/plain; charset=utf-8'}

    except Exception as err:
        return f"సాంకేతిక లోపం వచ్చింది: {str(err)}", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
  
