from flask import Flask, request, Response
import google.generativeai as genai
import requests
import os

app = Flask(__name__)

# API Keys
CRICKET_API_KEY = "5393947d-ab90-478e-ab15-6e9eb83989c1"
GEMINI_API_KEY = "AQ.Ab8RN6JCJlMqSZeblFh1OBzmiVRoKsCs11Hj0xFjUwhmmMCcmA"

# Google Gemini Configuration
genai.configure(api_key=GEMINI_API_KEY)

# సరి చేసిన కొత్త Gemini Model Name
model = genai.GenerativeModel('gemini-2.5-flash')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        # App నుండి వచ్చే డేటాని చదవడం
        data = request.get_json(silent=True) or {}
        user_message = str(data.get('message', '')).strip()

        if not user_message:
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

        # 3. Gemini AI ద్వారా సమాధానం (జార్విస్ మోడ్)
        else:
            prompt = (
                "నువ్వు ఒక అత్యంత తెలివైన, పవర్ ఫుల్ పర్సనల్ AI అసిస్టెంట్ 'జార్విస్' (Rajesh AI). "
                "కార్డియాలజీ, మెడిసిన్, బిఎస్సీ నర్సింగ్, బీకామ్, డిప్లమా మరియు ఇతర ఏ కోర్సు లేదా జనరల్ సంబంధిత ప్రశ్నలైనా "
                "చాలా స్పష్టంగా, పాయింట్ వారీగా, సులభంగా అర్థమయ్యే తెలుగులో సమాధానం ఇవ్వు.\n\n"
                f"ప్రశ్న: {user_message}"
            )
            response = model.generate_content(prompt)
            return Response(response.text, mimetype='text/plain; charset=utf-8')

    except Exception as e:
        # అసలైన ఎర్రర్ ఏంటో ప్రింట్ చేస్తుంది
        return Response(f"లోపం వివరాలు: {str(e)}", mimetype='text/plain; charset=utf-8')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
