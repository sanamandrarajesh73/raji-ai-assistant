from flask import Flask, request, Response
import requests
import os

app = Flask(__name__)

# నీ Cricket API Key
API_KEY = "5393947d-ab90-478e-ab15-6e9eb83989c1"

@app.route('/')
def home():
    return "Raji AI Assistant is Running Live!"

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json() or {}
    user_message = str(data.get('message', '')).lower()
    
    # లైవ్ క్రికెట్ మల్టీ-మ్యాచ్ లాజిక్
    if 'cricket' in user_message or 'క్రికెట్' in user_message:
        try:
            url = f"https://api.cricapi.com/v1/currentMatches?apikey={API_KEY}&offset=0"
            response = requests.get(url).json()
            matches = response.get('data', [])
            
            if matches:
                reply_text = "🏏 **టాప్ లైవ్ క్రికెట్ మ్యాచ్‌లు:**\n\n"
                # మొదటి 3 మ్యాచ్‌లను వరుసగా సేకరించడం
                top_matches = matches[:3]
                
                for idx, match in enumerate(top_matches, 1):
                    name = match.get('name', 'Live Match')
                    status = match.get('status', 'మ్యాచ్ జరుగుతోంది')
                    
                    reply_text += f"{idx}. {name}\n   📊 స్థితి: {status}\n\n"
                
                reply = reply_text.strip()
            else:
                reply = "ప్రస్తుతం ఎలాంటి లైవ్ క్రికెట్ మ్యాచ్‌లు అందుబాటులో లేవు నేస్తమా."
        except Exception:
            reply = "లైవ్ క్రికెట్ స్కోర్ సమాచారం అందడం లేదు, కాసేపటి తర్వాత ప్రయత్నించండి."

    elif 'tennis' in user_message or 'టెన్నిస్' in user_message:
        reply = "🎾 టెన్నిస్ అప్‌డేట్: ప్రసిద్ధ మ్యాచ్‌ల సమాచారం ప్రాసెస్ అవుతోంది."
    elif 'stock' in user_message or 'స్టాక్' in user_message:
        reply = "📈 స్టాక్ మార్కెట్: మార్కెట్ ప్రస్తుతం లైవ్ ట్రేడింగ్‌లో ఉంది."
    elif 'hi' in user_message or 'హాయ్' in user_message:
        reply = "హలో నేస్తమా! నేను రాజి AI అసిస్టెంట్‌ని. లైవ్ స్కోర్ కోసం క్రికెట్ బటన్ నొక్కండి."
    else:
        reply = f"మీ ప్రశ్న: '{user_message}' అందులోని వివరాలు ప్రాసెస్ అవుతున్నాయి."
    
    return Response(reply, mimetype='text/plain; charset=utf-8')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
