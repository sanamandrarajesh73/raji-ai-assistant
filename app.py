from flask import Flask, request, Response
import requests
import os

app = Flask(__name__)

# API Keys
CRICKET_API_KEY = "5393947d-ab90-478e-ab15-6e9eb83989c1"
GEMINI_API_KEY = "AQ.Ab8RN6J8-tetRqshwAkfiHzY85tJI9RNQVljMkE5_IUR0zMP0A"

@app.route('/chat', methods=['POST'])
def chat():
    try:
        # App Inventor నుండి వచ్చే డేటాని సెక్యూర్ గా రీడ్ చేయడం
        data = request.get_json(silent=True) or {}
        user_message = str(data.get('message', '')).strip()

        if not user_message:
            # ఒకవేళ యాప్ ప్లెయిన్ టెక్స్ట్ లేదా ఫారమ్ డేటా పంపితే:
            user_message = request.form.get('message', '') or request.data.decode('utf-8', errors='ignore')

        user_message_clean = user_message.lower().strip()

        # 1. క్రికెట్ విభాగం
        if 'cricket' in user_message_clean or 'క్రికెట్' in user_message_clean:
            url = f"https://api.cricapi.com/v1/currentMatches?apikey={CRICKET_API_KEY}&offset=0"
            matches = requests.get(url).json().get('data', [])
            live_matches = [m for m in matches if not m.get('matchEnded', False)]
            
            if live_matches:
                reply = "🏏 రాజేష్ AI - మ్యాచ్ ప్రిడిక్షన్స్ 🏏\n═════════════════════════\n\n"
                for match in live_matches:
                    name = match.get('name', 'Match')
                    teams = match.get('teams', [])
                    fav_team = teams[0] if len(teams) > 0 else "Team A"
                    reply += f"🏆 {name}\n⏰ సమయం: సాయంత్రం 3:30 PM\n─────────────\n⭐️ గెలిచే టీమ్: 👉 {fav_team}\n(ఈ మ్యాచ్ లో {fav_team} గెలిచే అవకాశం ఎక్కువ)\n\n"
                return Response(reply.strip(), mimetype='text/plain; charset=utf-8')
            else:
                return Response("ప్రస్తుతం ఎటువంటి లైవ్ మ్యాచ్‌లు లేవు నేస్తమా.", mimetype='text/plain; charset=utf-8')

        # 2. గ్రీటింగ్స్ (హాయ్ / Hallo)
        elif 'hallo' in user_message_clean or 'hello' in user_message_clean or 'హాయ్' in user_message_clean:
            return Response("హలో నేస్తమా! నేను నీ పర్సనల్ జార్విస్ AI ని. నీకు ఏ సందేహం ఉందో అడుగు (మెడికల్, కార్డియాలజీ, నర్సింగ్, బీకామ్ లేదా క్రికెట్ వివరాలు).", mimetype='text/plain; charset=utf-8')

        # 3. Gemini AI / సాధారణ ప్రశ్నలు (REST API ద్వారా నేరుగా కాల్ చేయడం)
        else:
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{
                    "parts": [{
                        "text": f"నువ్వు ఒక పవర్ ఫుల్ పర్సనల్ AI అసిస్టెంట్ 'జార్విస్' (Rajesh AI). కార్డియాలజీ, మెడిసిన్, బిఎస్సీ నర్సింగ్, బీకామ్ మరియు ఇతర ఏ కోర్సు సంబంధిత ప్రశ్నలైనా చాలా స్పష్టంగా, పాయింట్ వారీగా తెలుగులో సమాధానం ఇవ్వు.\n\nప్రశ్న: {user_message}"
                    }]
                }]
            }
            res = requests.post(gemini_url, json=payload, headers={'Content-Type': 'application/json'})
            
            if res.status_code == 200:
                result_json = res.json()
                ai_text = result_json['candidates'][0]['content']['parts'][0]['text']
                return Response(ai_text, mimetype='text/plain; charset=utf-8')
            else:
                return Response("నమస్కారం! నేను నీ పర్సనల్ జార్విస్ AI ని. నన్ను ఏ సబ్జెక్ట్ లేదా క్రికెట్ డౌట్ అయినా అడగొచ్చు.", mimetype='text/plain; charset=utf-8')

    except Exception as e:
        return Response("హలో నేస్తమా! నీ ప్రశ్నకు సమాధానం ఇవ్వడంలో చిన్న లోపం జరిగింది. మళ్లీ ప్రయత్నించు.", mimetype='text/plain; charset=utf-8')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
