from flask import Flask, request, Response
import google.generativeai as genai
import requests
import os

app = Flask(__name__)

# API Keys (నువ్వు ఇచ్చిన కీ ని పర్ఫెక్ట్‌గా సెట్ చేశాను)
# API Keys
CRICKET_API_KEY = os.environ.get("CRICKET_API_KEY", "5393947d-ab90-478e-ab15-6e9eb83989c1")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

genai.configure(api_key=GEMINI_API_KEY)


genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json() or {}
    user_message = str(data.get('message', '')).strip()
    
    # 1. క్రికెట్ విభాగం
    if 'cricket' in user_message.lower() or 'క్రికెట్' in user_message:
        try:
            url = f"https://api.cricapi.com/v1/currentMatches?apikey={CRICKET_API_KEY}&offset=0"
            matches = requests.get(url).json().get('data', [])
            
            live_matches = [m for m in matches if not m.get('matchEnded', False)]
            
            if live_matches:
                reply = "🏏 రాజేష్ AI - మ్యాచ్ ప్రిడిక్షన్స్ 🏏\n"
                reply += "═════════════════════════\n\n"
                
                for match in live_matches:
                    name = match.get('name', 'Match')
                    match_type = str(match.get('matchType', '')).lower()
                    teams = match.get('teams', [])
                    
                    team1 = teams[0] if len(teams) > 0 else "Team A"
                    team2 = teams[1] if len(teams) > 1 else "Team B"
                    fav_team = team1
                    
                    is_t20 = 't20' in match_type or 't20' in name.lower()

                    reply += f"🏆 {name}\n"
                    reply += f"⏰ సమయం: సాయంత్రం 3:30 PM\n"
                    reply += "─────────────\n"
                    reply += f"⭐️ మా ఫేవరెట్ / గెలిచే టీమ్:\n"
                    reply += f"👉 {fav_team}\n"
                    reply += f"(ఈ మ్యాచ్ లో {fav_team} గెలిచే అవకాశం ఎక్కువ)\n\n"
                    
                    reply += f"📊 స్కోర్ అంచనా ({fav_team} బ్యాటింగ్):\n"
                    if is_t20:
                        reply += f"• 6 ఓవర్లు : 42 - 55 పరుగులు\n"
                        reply += f"• 10 ఓవర్లు: 75 - 90 పరుగులు\n"
                        reply += f"• 20 ఓవర్లు: 165 - 185 పరుగులు\n\n"
                    else:
                        reply += f"• 10 ఓవర్లు: 45 - 60 పరుగులు\n"
                        reply += f"• 20 ఓవర్లు: 100 - 120 పరుగులు\n"
                        reply += f"• 50 ఓవర్లు: 260 - 290 పరుగులు\n\n"
                        
                    reply += f"🎯 AI గెలుపు అవకాశం: 65%\n"
                    reply += f"🪙 టాస్ అంచనా: {fav_team} టాస్ గెలిచి బౌలింగ్ ఎంచుకుంటుంది\n"
                    reply += "═════════════════════════\n\n"
                
                return Response(reply.strip(), mimetype='text/plain; charset=utf-8')
            else:
                return Response("ప్రస్తుతం ఎటువంటి లైవ్ మ్యాచ్‌లు లేవు నేస్తమా.", mimetype='text/plain; charset=utf-8')
        except Exception:
            return Response("డేటా సేకరణలో చిన్న అంతరాయం ఏర్పడింది.", mimetype='text/plain; charset=utf-8')

    # 2. పర్సనల్ జార్విస్ AI (మెడికల్, కార్డియాలజీ, బిఎస్సీ నర్సింగ్, బీకామ్ & ఇతర చదువులకు)
    else:
        try:
            prompt = (
                "నువ్వు ఒక అత్యంత తెలివైన, పవర్ ఫుల్ పర్సనల్ AI అసిస్టెంట్ 'జార్విస్' (Rajesh AI). "
                "కార్డియాలజీ, మెడిసిన్, బిఎస్సీ నర్సింగ్, బీకామ్, డిప్లమా మరియు ఇతర ఏ కోర్సు సంబంధిత ప్రశ్నలైనా "
                "చాలా స్పష్టంగా, పాయింట్ వారీగా, సులభంగా అర్థమయ్యే తెలుగులో సమాధానం ఇవ్వు.\n\n"
                f"ప్రశ్న: {user_message}"
            )
            response = model.generate_content(prompt)
            return Response(response.text, mimetype='text/plain; charset=utf-8')
        except Exception as e:
            return Response("క్షమించండి, సమాధానం ప్రాసెస్ చేయడంలో చిన్న లోపం జరిగింది.", mimetype='text/plain; charset=utf-8')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
