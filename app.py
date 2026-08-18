from flask import Flask, request, jsonify
import requests
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
    return jsonify({"response": reply})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
  
