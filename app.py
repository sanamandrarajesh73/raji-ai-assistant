from flask import Flask, request, Response
import json
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Raji AI Assistant is Running Live!"

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json() or {}
    user_message = data.get('message', '')
    
    # Simple Response Logic
    reply = f"హలో! మీ మెసేజ్ అందింది: {user_message}"
    
    # ensure_ascii=False వల్ల తెలుగు అక్షరాలు విడిపోకుండా స్పష్టంగా వస్తాయి
    return Response(json.dumps({"response": reply}, ensure_ascii=False), mimetype='application/json')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    
  
