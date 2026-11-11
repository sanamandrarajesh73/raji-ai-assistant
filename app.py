
import os
from flask import Flask, request, jsonify, render_template_string
from google import genai
from google.genai import types

app = Flask(__name__)

# ==============================
# PHOENIX AI CONFIGURATION
# ==============================

API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

MODEL_NAME = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash"
).strip()

FALLBACK_MODEL = os.getenv(
    "GEMINI_FALLBACK_MODEL",
    "gemini-2.5-flash"
).strip()

client = genai.Client(api_key=API_KEY) if API_KEY else None

SYSTEM_PROMPT = """
You are PHOENIX AI, a friendly all-round personal AI assistant.

Your creator is Rajesh.

PERSONALITY:
- Be friendly, intelligent and helpful.
- Understand the user's question before answering.
- Give accurate and honest answers.
- Never invent facts, prices, news or live sports scores.
- Admit when you do not know something.

LANGUAGE:
- Understand Telugu and English.
- Reply in simple Telugu when the user speaks Telugu.
- Reply in simple English when the user speaks English.
- Use both languages when requested.

SKILLS:
- Education and learning.
- English speaking practice.
- Coding and programming.
- Artificial Intelligence and technology.
- General knowledge.
- Cricket and tennis information.
- Finance education and stock market explanations.
- YouTube and video creation.
- Daily life assistance.

IMPORTANT:
- Explain difficult topics step by step.
- Keep answers clear and easy to understand.
- Do not use unnecessary Markdown symbols.
- Never promise guaranteed profits.
- For live information, clearly say when live data is unavailable.
- Be respectful and encouraging.
"""

# ==============================
# WEB PAGE
# ==============================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport"
content="width=device-width, initial-scale=1.0">

<title>PHOENIX AI</title>

<style>
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    padding: 20px;
    background: #091827;
    color: white;
    font-family: Arial, sans-serif;
}

.container {
    max-width: 650px;
    margin: 30px auto;
    padding: 25px;
    background: #17283e;
    border-radius: 18px;
    text-align: center;
}

h1 {
    font-size: 30px;
    margin-bottom: 20px;
}

.subtitle {
    font-size: 20px;
    margin-bottom: 35px;
}

input {
    width: 100%;
    padding: 16px;
    border: none;
    border-radius: 10px;
    font-size: 18px;
}

button {
    margin-top: 18px;
    padding: 16px 38px;
    border: none;
    border-radius: 10px;
    background: #ff0080;
    color: white;
    font-size: 18px;
    cursor: pointer;
}

button:disabled {
    opacity: 0.6;
}

#answer {
    margin-top: 30px;
    padding: 20px;
    background: #385b7c;
    border-radius: 10px;
    font-size: 18px;
    line-height: 1.6;
    text-align: left;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
}

</style>
</head>

<body>

<div class="container">

<h1>🦅 PHOENIX AI</h1>

<div class="subtitle">
ఆల్ రౌండర్ రక్షకుడు & సహాయకుడు 💡
</div>

<form id="chatForm">

<input
type="text"
id="message"
placeholder="Ask Phoenix anything..."
required
>

<button id="sendButton" type="submit">
Send
</button>

</form>

<div id="answer">
Hello! I am Phoenix AI. How can I help you?
</div>

</div>

<script>

const form = document.getElementById("chatForm");
const input = document.getElementById("message");
const answer = document.getElementById("answer");
const button = document.getElementById("sendButton");

form.addEventListener("submit", async function(e) {

    e.preventDefault();

    const message = input.value.trim();

    if (!message) return;

    button.disabled = true;
    answer.textContent = "Phoenix AI is thinking...";

    try {

        const response = await fetch("/chat", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                message: message
            })

        });

        const result = await response.json();

        answer.textContent =
            result.reply || result.data || "No response received.";

    } catch (error) {

        answer.textContent =
            "Connection error. Please try again.";

    }

    button.disabled = false;

});

</script>

</body>
</html>
"""

# ==============================
# AI RESPONSE FUNCTION
# ==============================

def generate_answer(message):

    if not API_KEY or client is None:
        raise RuntimeError(
            "GEMINI_API_KEY is missing in Render Environment."
        )

    prompt = (
        SYSTEM_PROMPT
        + "\n\nUser Question:\n"
        + message
    )

    models_to_try = [MODEL_NAME]

    if FALLBACK_MODEL and FALLBACK_MODEL != MODEL_NAME:
        models_to_try.append(FALLBACK_MODEL)

    last_error = None

    for model in models_to_try:

        try:

            response = client.models.generate_content(

                model=model,

                contents=prompt,

                config=types.GenerateContentConfig(

                    temperature=0.6,

                    max_output_tokens=1500

                )

            )

            answer = response.text

            if answer and answer.strip():
                return answer.strip()

            last_error = RuntimeError(
                "AI returned an empty response."
            )

        except Exception as error:

            last_error = error

    raise RuntimeError(str(last_error))


# ==============================
# JSON RESPONSE
# ==============================

def make_response(data, success=True):

    return jsonify({

        "status": "success" if success else "error",

        "title": "PHOENIX AI",

        "data": data,

        "reply": data

    })


# ==============================
# HOME PAGE
# ==============================

@app.route("/", methods=["GET"])
def home():

    return render_template_string(HTML_TEMPLATE)


# ==============================
# HEALTH CHECK
# ==============================

@app.route("/health", methods=["GET"])
def health():

    return jsonify({

        "status": "online",

        "service": "PHOENIX AI",

        "model": MODEL_NAME,

        "fallback_model": FALLBACK_MODEL,

        "api_key_configured": bool(API_KEY)

    })


# ==============================
# CHAT API
# ==============================

@app.route("/chat", methods=["GET", "POST"])
def chat():

    if request.method == "GET":
        return make_response(
            "PHOENIX AI Chat API is ready."
        )

    return process_message()


# ==============================
# BRAIN API
# ==============================

@app.route("/brain", methods=["GET", "POST"])
def brain():

    if request.method == "GET":
        return make_response(
            "PHOENIX AI Brain is ready."
        )

    return process_message()


# ==============================
# KODULAR RUN API
# ==============================

@app.route("/run", methods=["GET", "POST"])
def run():

    return process_message()


# ==============================
# MESSAGE PROCESSOR
# ==============================

def process_message():

    try:

        if request.method == "GET":

            message = (
                request.args.get("query")
                or request.args.get("message")
                or ""
            )

        else:

            body = request.get_json(silent=True) or {}

            message = (
                body.get("message")
                or body.get("query")
                or body.get("prompt")
                or body.get("data")
                or request.form.get("message")
                or ""
            )

        message = str(message).strip()

        if not message:

            return make_response(
                "Please enter a question.",
                False
            ), 400

        if len(message) > 10000:

            return make_response(
                "Message is too long. Please shorten it.",
                False
            ), 400

        reply = generate_answer(message)

        return make_response(reply)

    except Exception as error:

        print("PHOENIX ERROR:", str(error))

        return make_response(
            "Phoenix AI Error: " + str(error),
            False
        ), 500


# ==============================
# START SERVER
# ==============================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
    
