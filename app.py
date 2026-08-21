from flask import Flask, request, Response
import requests
import os

app = Flask(__name__)

API_KEY = "5393947d-ab90-478e-ab15-6e9eb83989c1"

@app.route('/')
def home():
    return "Rajesh Cricket AI Assistant is Running Live!"

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json() or {}
    user_message = str(data.get('message', '')).lower()
    
    if 'cricket' in user_message or 'క్రికెట్' in user_message:
        try:
            url = f"https://api.cricapi.com/v1/currentMatches?apikey={API_KEY}&offset=0"
            response = requests.get(url).json()
            matches = response.get('data', [])
            
            # ఇక్కడ మనం పాత మ్యాచ్‌లను పూర్తిగా ఫిల్టర్ చేస్తున్నాం
            # matchEnded = False ఉన్న వాటిని మాత్రమే తీసుకుంటుంది
            live_and_upcoming = [m for m in matches if not m.get('matchEnded', True)]
            
            if live_and_upcoming:
                reply_text = "🔥 **RAJESH CRICKET AI - LIVE & UPCOMING** 🔥\n"
                reply_text += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                # మొదటి 3 మ్యాచ్‌లను చూపిస్తుంది
                for idx, match in enumerate(live_and_upcoming[:3], 1):
                    name = match.get('name', 'Match')
                    status = match.get('status', 'ఆరంభం కానుంది')
                    
                    scores = match.get('score', [])
                    if scores and isinstance(scores, list):
                        score_text = " | ".join([f"{s.get('inning', '')}: {s.get('r', 0)}/{s.get('w', 0)} ({s.get('o', 0)} ov)" for s in scores])
                    else:
                        score_text = "మ్యాచ్ ఇంకా మొదలవ్వలేదు"

                    reply_text += f"🏏 **MATCH {idx}: {name}**\n"
                    reply_text += f"📊 **Score:** {score_text}\n"
                    reply_text += f"📌 **Status:** {status}\n"
                    reply_text += "───────────────────────\n\n"
                
                reply = reply_text.strip()
            else:
                reply = "ప్రస్తుతం లైవ్‌లో గానీ, ఈరోజు జరగబోయే గానీ ఎటువంటి మ్యాచ్‌లు లేవు నేస్తమా. కాసేపటి తర్వాత ప్రయత్నించండి!"
        except Exception as e:
            reply = "సర్వర్ నుండి సమాచారం అందడం లేదు. మళ్లీ ప్రయత్నించండి."

    elif 'hi' in user_message or 'హాయ్' in user_message:
        reply = "హలో నేస్తమా! నేను రాజేష్ క్రికెట్ AI ని. లైవ్ మ్యాచ్‌ల కోసం క్రికెట్ అని అడగండి."
    else:
        reply = f"మీరు అడిగిన '{user_message}' వివరాలు అందుబాటులో లేవు."
    
    return Response(reply, mimetype='text/plain; charset=utf-8')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
