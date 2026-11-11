import os
from flask import Flask, render_template_string, request, jsonify
from google import genai

app = Flask(__name__)

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="te">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PHOENIX TENNIS LIVE</title>
    <style>
        body { background-color: #0d1b2a; color: white; font-family: Arial, sans-serif; padding: 20px; text-align: center; }
        .chat-box { max-width: 600px; margin: auto; background: #1b263b; padding: 20px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
        input { width: 80%; padding: 12px; margin: 10px 0; border-radius: 5px; border: none; font-size: 16px; }
        button { padding: 12px 25px; background: #ff007f; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold; }
        button:hover { background: #e00070; }
        .response { margin-top: 20px; text-align: left; background: #415a77; padding: 15px; border-radius: 5px; white-space: pre-wrap; font-size: 15px; }
    </style>
</head>
<body>
    <div class="chat-box">
        <h2>🦅 PHOENIX TENNIS LIVE</h2>
        <p>ఆల్ రౌండర్ రక్షకుడు & సహాయకుడు 💡</p>
        <input type="text" id="userInput" placeholder="ఉదాహరణకు: 'tennis live' అని అడగండి...">
        <br>
        <button onclick="sendMessage()">Send</button>
        <div class="response" id="responseArea">లైవ్ మ్యాచ్‌ల కోసం 'tennis live' అని అడగండి.<br>రాబోయే మ్యాచ్‌ల కోసం 'tennis upcoming' అని అడగండి.</div>
    </div>

    <script>
        async function sendMessage() {
            let text = document.getElementById("userInput").value;
            let responseArea = document.getElementById("responseArea");
            if (!text) return;
            
            responseArea.innerHTML = "లోడ్ అవుతోంది...";

            try {
                let res = await fetch("/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message: text })
                });
                let data = await res.json();
                responseArea.innerHTML = data.reply;
            } catch (error) {
                responseArea.innerHTML = "నెట్వర్క్ ఎర్రర్ వచ్చింది. దయచేసి మళ్లీ ప్రయత్నించండి.";
            }
        }
    </script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "")
    try:
        prompt = f"You are a tennis live assistant named Phoenix. User asks: {user_message}. Provide accurate tennis live scores, updates or upcoming matches information in Telugu or English as requested."
        
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
        )
        return jsonify({"reply": response.text})
    except Exception as e:
        return jsonify({"reply": f"ఎర్రర్ వచ్చింది: ({str(e)})"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
        
