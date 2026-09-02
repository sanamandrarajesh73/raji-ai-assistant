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
            return "API Key నాట్ ఫౌండ్: Render లో GEMINI_API_KEY సరిగ్గా ఉందో లేదో చూడండి.", 200

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
            return "దయచేసి ప్రశ్న టైప్ చేయండి.", 400

        system_context = (
            "యు ఆర్ ఫీనిక్స్ AI (Phoenix AI) - ఆల్ రౌండర్ రక్షకుడు & సహాయకుడు. "
            "సమాధానాలు స్పష్టంగా తెలుగు భాషలో అందించు.\n\n"
            f"యూజర్ ప్రశ్న: {user_prompt}"
        )

        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(system_context)

        if response and response.text:
            return response.text, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        else:
            return "AI నుండి ఖాళీ రెస్పాన్స్ వచ్చింది.", 200

    except Exception as err:
        return f"ఎర్రర్ వివరాలు: {str(err)}", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
