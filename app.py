import os
import requests
from flask import Flask, request

app = Flask(__name__)

API_KEY = os.environ.get("GEMINI_API_KEY")

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

        system_prompt = (
            "యు ఆర్ ఫీనిక్స్ AI (Phoenix AI) - ఆల్ రౌండర్ రక్షకుడు & సహాయకుడు. "
            f"సమాధానాలు స్పష్టంగా తెలుగు భాషలో అందించు.\n\nయూజర్ ప్రశ్న: {user_prompt}"
        )

        # Gemini 3.6 Flash మోడల్
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={API_KEY}"
        
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{
                "parts": [{"text": system_prompt}]
            }]
        }

        response = requests.post(url, json=payload, headers=headers)
        res_data = response.json()

        if response.status_code == 200:
            ai_text = res_data['candidates'][0]['content']['parts'][0]['text']
            
            # Markdown గుర్తులను (Stars, Dashes, Hashtags) క్లీన్ చేసే కోడ్
            clean_text = ai_text.replace('**', '').replace('*', '').replace('#', '')
            
            return clean_text, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        else:
            error_msg = res_data.get('error', {}).get('message', 'గూగుల్ సర్వర్లు బిజీగా ఉన్నాయి.')
            return f"గూగుల్ API లోపం ({response.status_code}): {error_msg}", 200

    except Exception as err:
        return f"ఎర్రర్ వివరాలు: {str(err)}", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
