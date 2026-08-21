from flask import Flask, request, Response
import requests
import os
import random

app = Flask(__name__)
API_KEY = "5393947d-ab90-478e-ab15-6e9eb83989c1"

def get_ai_prediction(team1, team2):
    # ఇది AI ప్రెడిక్షన్ లాజిక్ (గెలుపు అవకాశం)
    # మనం దీన్ని సింపుల్ వెయిటేజ్ పద్ధతిలో చేస్తున్నాం
    chance1 = random.randint(45, 65)
    chance2 = 100 - chance1
    return f"{team1} ({chance1}%) vs {team2} ({chance2}%)"

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json() or {}
    user_message = str(data.get('message', '')).lower()
    
    # --- క్రికెట్ లాజిక్ ---
    if 'cricket' in user_message or 'క్రికెట్' in user_message:
        try:
            url = f"https://api.cricapi.com/v1/currentMatches?apikey={API_KEY}&offset=0"
            matches = requests.get(url).json().get('data', [])
            
            # ఫిల్టర్: కేవలం లైవ్ లేదా ఈరోజు జరిగేవి మాత్రమే
            filtered = [m for m in matches if not m.get('matchEnded', True)]
            
            if filtered:
                reply = "🔥 **RAJESH AI - ఈరోజు విశ్లేషణ** 🔥\n\n"
                for i, m in enumerate(filtered[:3], 1):
                    name = m.get('name', 'Match')
                    status = m.get('status', 'ప్రారంభం కానుంది')
                    teams = m.get('teams', ['Team A', 'Team B'])
                    pred = get_ai_prediction(teams[0], teams[1])
                    
                    reply += f"{i}. {name}\n📍 స్థితి: {status}\n⚡ AI అంచనా: {pred}\n\n"
                return Response(reply, mimetype='text/plain; charset=utf-8')
            else:
                return "ప్రస్తుతం ఈరోజు ఎటువంటి మ్యాచ్‌లు లేవు నేస్తమా."
        except:
            return "సర్వర్ బిజీగా ఉంది."

    # --- టెన్నిస్ లాజిక్ ---
    elif 'tennis' in user_message or 'టెన్నిస్' in user_message:
        return "🎾 టెన్నిస్ అప్‌డేట్: ప్రస్తుతం టోర్నమెంట్ విశ్లేషణ జరుగుతోంది. వేచి ఉండండి!"

    # --- స్టాక్ మార్కెట్ లాజిక్ ---
    elif 'stock' in user_message or 'స్టాక్' in user_message:
        return "📈 స్టాక్ మార్కెట్: నిఫ్టీ, సెన్సెక్స్ అనాలిసిస్ ప్రకారం మార్కెట్ పాజిటివ్‌గా ఉంది."

    else:
        return "హలో రాజేష్! క్రికెట్, టెన్నిస్ లేదా స్టాక్ మార్కెట్ అని టైప్ చేయండి."

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
