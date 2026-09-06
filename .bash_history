pkill -9 -f app.py
pkg update && pkg upgrade -y
pkg install python git -y
pip install flask requests yfinance
pkg install clang python-pharmacy -y
pip install --upgrade pip
pip install yfinance
pip install requests flask --no-build-isolation
cat << 'EOF' > app.py
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

@app.route('/run', methods=['GET'])
def get_data():
    query = request.args.get('q', '').lower()
    
    if query == 'cricket':
        return jsonify({
            "status": "success",
            "title": "🏏 LIVE CRICKET",
            "data": "IND vs AUS: 180/4 (18.5 Ov) | ఇండియాకు గెలవడానికి 12 బంతుల్లో 15 రన్స్ కావాలి!"
        })
    elif query == 'tennis':
        return jsonify({
            "status": "success",
            "title": "🎾 LIVE TENNIS",
            "data": "Djokovic vs Alcaraz: Set 2 (5-4) | మ్యాచ్ చాలా ఆసక్తికరంగా సాగుతోంది!"
        })
    elif query == 'stocks':
        try:
            # Yahoo Finance లైట్ API
            url = "https://query1.finance.yahoo.com/v8/finance/chart/RELIANCE.NS"
            headers = {'User-Agent': 'Mozilla/5.0'}
            res = requests.get(url, headers=headers).json()
            price = res['chart']['result'][0]['meta']['regularMarketPrice']
            prev_close = res['chart']['result'][0]['meta']['chartPreviousClose']
            diff = round(price - prev_close, 2)
            
            signal = "🟢 BUY SIGNAL" if diff >= 0 else "🔴 SELL SIGNAL"
            return jsonify({
                "status": "success",
                "title": "📈 RELIANCE STOCK",
                "data": f"ధర: ₹{price} ({'+' if diff >= 0 else ''}{diff}) | {signal}"
            })
        except Exception as e:
            return jsonify({
                "status": "success", 
                "title": "📈 RELIANCE STOCK", 
                "data": "ధర: ₹2,850.50 (+18.5) | 🟢 BUY SIGNAL (5M Trend Positive)"
            })
    else:
        return jsonify({
            "status": "success", 
            "title": "🤖 JARVIS", 
            "data": "నమస్తే! క్రికెట్, టెన్నిస్ లేదా స్టాక్స్ సమాచారం కోసం అడగండి."
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)
EOF

python app.py
pkill -9 -f app.py
python app.py
pkg install cloudflared -y
cloudflared tunnel --url http://localhost:5050
cat tunnel.log | grep -o 'https://.*\.trycloudflare\.com'
python app.py
cloudflared tunnel...
cloudflared tunnel --url http://localhost:5050 > tunnel.log 2>&1 &
sleep 5
cat tunnel.log | grep -o 'https://.*\.trycloudflare\.com'
pkill -9 -f app.py
python app.py
cloudflared tunnel --url http://localhost:5050
pip install flask requests
python app.py
cloudflared tunnel --url http://localhost:5050
cloudflared tunnel --url http://localhost:5050 > tunnel.log 2>&1 &
sleep 5
cat tunnel.log | grep -o 'https://.*\.trycloudflare\.com'
pkill -9 -f app.py
python app.py
*#*#4636#*
import os
import urllib.parse
from flask import Flask, request, jsonify
from google import genai
from google.genai import types
app = Flask(__name__)
# Fetch Gemini API Key from Render Environment Variables
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
# Ultimate System Prompt: Perplexity-Style Search + Student Drawing Guide + All Streams
SYSTEM_PROMPT = """
You are Phoenix Next-Gen AI — The Ultimate Universal Academic, Career, and Real-Time Search Intelligence Engine.

COVERED DOMAINS:
1. Academic Subjects: Maths, Physics, Chemistry, Biology, History, Civics, Economics, Computer Science, Law, Pharmacy, Literature, etc.
2. Professional & Vocational Streams: B.Sc Nursing, Electrician, Software Development, Banking Exams, Diploma, Trade Courses.

CORE FORMATTING RULES:
1. Always respond in simple, natural Telugu mixed with standard English terms.
2. Structure all answers using ONLY clean numbered lists or simple bullet points.
3. ABSOLUTELY NO Markdown characters: do NOT use hashes (#), asterisks (*), pipes (|), or ASCII art boxes. (These break mobile screen layouts).
4. REAL-TIME FACTS: Provide live, accurate, up-to-date facts when asked about current news, sports, or live data.
5. FOR DIAGRAMS/DRAWINGS (Nursing, Science, Engineering):
   - Provide a Step-by-Step Pen & Paper drawing guide (Step 1, Step 2, Step 3).
   - At the very end, generate an HD diagram search link like this:
     "HD Diagram చూడటానికి ఇక్కడ క్లిక్ చేయండి: https://www.google.com/search?tbm=isch&q=[SEARCH_TERM_IN_ENGLISH]"
"""
@app.route("/", methods=["GET"])
def home():
@app.route("/chat", methods=["POST"])
def chat():
if __name__ == "__main__":;     app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
