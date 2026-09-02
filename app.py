import os
from flask import Flask, request
import google.generativeai as genai

app = Flask(__name__)

API_KEY = os.environ.get("GEMINI_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'GET':
        return "Phoenix AI Backend is Active!"

    try:
        if not API_KEY:
            return "API Key నాట్ ఫౌండ్!", 200

        user_prompt = None

        if request.is_json:
            data = request.get_json(silent=True)
            if data:
                user_prompt = data.get('prompt')
        
        if not user_prompt and request.form:
            user_prompt = request.form.get('prompt')

        if not user_prompt:
            user_prompt = request.get_data(as_text=True)

        if not user_prompt or not user_prompt.strip():
            return "దయచేసి ప్రశ్న టైప్ చేయండి.", 200

        system_context = (
            "యు ఆర్ ఫీనిక్స్ AI (Phoenix AI) - ఆల్ రౌండర్ రక్షకుడు & సహాయకుడు. "
            "సమాధానాలు స్పష్టంగా తెలుగు భాషలో అందించు.\n\n"
            f"యూజర్ ప్రశ్న: {user_prompt}"
        )

        # models/ అని స్పష్టంగా మోడల్ పాత్ నిర్దేశించబడింది
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        response = model.generate_content(system_context)

        if response and hasattr(response, 'text') and response.text:
            return response.text, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        else:
            return "AI నుండి స్పందన రాలేదు.", 200

    except Exception as err:
        return f"ఎర్రర్ వివరాలు: {str(err)}", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
