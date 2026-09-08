from flask import Flask, request, jsonify, json
import requests

app = Flask(__name__)

@app.route('/run', methods=['GET'])
def get_data():
    query = request.args.get('query', '').strip().lower()

    if not query:
        msg = "దయచేసి ఏదైనా ప్రశ్నించండి లేదా మాట్లాడండి!"
        title = "🤖 PHOENIX AI"
    elif query == 'cricket':  
        msg = "IND vs AUS: 180/4 (18.5 Ov) | ఇండియాకు గెలవడానికి 12 బంతుల్లో 15 రన్స్ కావాలి!"
        title = "🏏 LIVE CRICKET"
    elif query == 'tennis':  
        msg = "Djokovic vs Alcaraz: Set 2 (5-4) | మ్యాచ్ చాలా ఆసక్తికరంగా సాగుతోంది!"
        title = "🎾 LIVE TENNIS"
    elif query == 'stocks':  
        try:  
            url = "https://query1.finance.yahoo.com/v8/finance/chart/RELIANCE.NS"  
            headers = {'User-Agent': 'Mozilla/5.0'}  
            res = requests.get(url, headers=headers).json()  
            price = res['chart']['result'][0]['meta']['regularMarketPrice']  
            prev_close = res['chart']['result'][0]['meta']['chartPreviousClose']  
            diff = round(price - prev_close, 2)  
            signal = "🟢 BUY SIGNAL" if diff >= 0 else "🔴 SELL SIGNAL"  
            msg = f"ధర: ₹{price} ({'+' if diff >= 0 else ''}{diff}) | {signal}"
            title = "📈 RELIANCE STOCK"
        except Exception:  
            msg = "ధర: ₹2,850.50 (+18.5) | 🟢 BUY SIGNAL (5M Trend Positive)"
            title = "📈 RELIANCE STOCK"
    else:  
        msg = f"నమస్తే! మీరు '{query}' అని అడిగారు. నేను మీ PHOENIX AI ని, క్రికెట్, టెన్నిస్ లేదా స్టాక్స్ గురించి అడగండి."
        title = "🤖 PHOENIX AI"

    return jsonify({
        "status": "success",
        "title": title,
        "data": msg
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)
