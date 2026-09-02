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

        # నీ API Key కి సపోర్ట్ చేసే మోడల్స్ లిస్ట్ తెలుసుకోవడం
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        return f"అందుబాటులో ఉన్న మోడల్స్: {', '.join(available_models)}", 200

    except Exception as err:
        return f"ఎర్రర్ వివరాలు: {str(err)}", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
