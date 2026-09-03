 import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

API_KEY = os.environ.get("GEMINI_API_KEY")

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'GET':
        return "Phoenix AI Backend is Active!", 200

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

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={API_KEY}"
        
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{
                "parts": [{"text": system_prompt}]
            }]
        }

        # 15 సెకన్ల టైమ్‌అవుట్ పరిమితి
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        res_data = response.json()

        if response.status_code == 200:
            ai_text = res_data['candidates'][0]['content']['parts'][0]['text']
            clean_text = ai_text.replace('**', '').replace('*', '').replace('#', '')
            return clean_text, 200, {'Content-Type': 'text/plain; charset=utf-8'}
            
        elif response.status_code == 429:
            return "చాలా రిక్వెస్ట్‌లు వచ్చాయి. దయచేసి ఒక 30 సెకన్లు ఆగి మళ్లీ ప్రయత్నించండి.", 200
        else:
            return "సర్వర్ బిజీగా ఉంది. దయచేసి మళ్లీ ప్రయత్నించండి.", 200

    except Exception as err:
        return "సర్వర్ స్పందించడానికి ఎక్కువ సమయం తీసుకుంటోంది. మళ్లీ ప్రయత్నించండి.", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
