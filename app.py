import os
from flask import Flask, request, jsonify
from flask_cors import CORS

from openai import OpenAI
from google import genai
from google.genai import types


# =========================================================
# 🦅 PHOENIX AI V2
# Dual AI Intelligence System
# OpenAI + Gemini + Live Web + Smart Router + Fallback
# =========================================================

app = Flask(__name__)
CORS(app)


# =========================================================
# 🔐 API CLIENTS
# =========================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

openai_client = None
gemini_client = None

if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)


# =========================================================
# 🧠 MODEL SETTINGS
# =========================================================

# Render Environment Variables నుంచి model names మార్చుకోవచ్చు.
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


# =========================================================
# 🦅 PHOENIX SYSTEM INTELLIGENCE
# =========================================================

PHOENIX_INSTRUCTIONS = """
You are PHOENIX AI, an advanced all-round AI assistant.

Creator: Rajesh

Your goals:

1. Give accurate, useful and practical answers.
2. Think deeply before answering.
3. Never invent facts when reliable information is available.
4. When current information is needed, use live web grounding/search.
5. Clearly separate facts, estimates, opinions and predictions.
6. If information is uncertain, say so instead of pretending certainty.
7. Explain difficult subjects in simple Telugu when the user speaks Telugu.
8. You can answer in English when the user asks for English.
9. Help with technology, programming, education, science,
   finance, business, productivity, general knowledge and creativity.
10. Generate original ideas, alternatives and solutions.
11. For coding problems, provide working and secure code.
12. Never expose API keys, passwords or secret credentials.
13. For important claims, prefer verifiable sources.
14. Do not promise 100% accuracy or guaranteed future results.

Phoenix should behave like a helpful intelligent orchestrator,
not like a blindly confident chatbot.
"""


# =========================================================
# 🔎 QUESTION CLASSIFIER
# =========================================================

def needs_live_information(text):
    keywords = [
        "today", "latest", "live", "now", "current",
        "ఈరోజు", "ఇప్పుడు", "తాజా", "లైవ్",
        "ప్రస్తుతం", "నేటి", "ఇప్పటి",
        "news", "price", "stock price", "weather",
        "score", "match", "market"
    ]

    text_lower = text.lower()

    return any(word.lower() in text_lower for word in keywords)


def is_coding_question(text):
    keywords = [
        "python", "javascript", "java", "flutter",
        "kodular", "android", "api", "flask",
        "code", "coding", "bug", "error",
        "కోడింగ్", "కోడ్", "ఎర్రర్"
    ]

    text_lower = text.lower()

    return any(word.lower() in text_lower for word in keywords)


def needs_deep_reasoning(text):
    keywords = [
        "deep research",
        "compare",
        "analysis",
        "analyze",
        "strategy",
        "architecture",
        "why",
        "how to build",
        "పూర్తిగా",
        "విశ్లేషణ",
        "పోల్చి",
        "ఎందుకు",
        "ఎలా తయారు"
    ]

    text_lower = text.lower()

    return any(word.lower() in text_lower for word in keywords)


# =========================================================
# 🤖 OPENAI ENGINE
# =========================================================

def ask_openai(question, live=False):

    if not openai_client:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    tools = []

    # Live information కోసం OpenAI web search
    if live:
        tools.append({
            "type": "web_search_preview"
        })

    response = openai_client.responses.create(
        model=OPENAI_MODEL,
        instructions=PHOENIX_INSTRUCTIONS,
        input=question,
        tools=tools
    )

    return response.output_text.strip()


# =========================================================
# 💎 GEMINI ENGINE
# =========================================================

def ask_gemini(question, live=False):

    if not gemini_client:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    tools = []

    # Gemini Google Search grounding
    if live:
        tools.append(
            types.Tool(
                google_search=types.GoogleSearch()
            )
        )

    config = types.GenerateContentConfig(
        system_instruction=PHOENIX_INSTRUCTIONS,
        tools=tools
    )

    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=question,
        config=config
    )

    return response.text.strip()


# =========================================================
# 🧠 DUAL-BRAIN SYNTHESIS
# =========================================================

def synthesize_answers(question, answer_a, answer_b):

    if not openai_client:
        return answer_a or answer_b

    synthesis_prompt = f"""
You are the final Phoenix AI answer engine.

User question:
{question}

AI A:
{answer_a}

AI B:
{answer_b}

Create ONE final answer.

Rules:
- Compare both answers.
- Remove contradictions when possible.
- Do not blindly trust either answer.
- Keep correct useful information.
- Do not invent missing facts.
- If there is uncertainty, clearly mention it.
- Give the user a direct answer first.
- Then give useful explanation.
- Answer in fluent Telugu if the question is Telugu.
- Keep the response readable.
"""

    response = openai_client.responses.create(
        model=OPENAI_MODEL,
        instructions=PHOENIX_INSTRUCTIONS,
        input=synthesis_prompt
    )

    return response.output_text.strip()


# =========================================================
# 🧭 PHOENIX SMART ROUTER
# =========================================================

def phoenix_engine(question):

    live = needs_live_information(question)
    coding = is_coding_question(question)
    deep = needs_deep_reasoning(question)

    # -----------------------------------------------------
    # 1️⃣ Deep questions → Dual AI
    # -----------------------------------------------------

    if deep:

        openai_answer = None
        gemini_answer = None

        try:
            openai_answer = ask_openai(question, live=live)
        except Exception as e:
            openai_answer = f"OpenAI unavailable: {str(e)}"

        try:
            gemini_answer = ask_gemini(question, live=live)
        except Exception as e:
            gemini_answer = f"Gemini unavailable: {str(e)}"

        return synthesize_answers(
            question,
            openai_answer,
            gemini_answer
        )


    # -----------------------------------------------------
    # 2️⃣ Coding → OpenAI
    # -----------------------------------------------------

    if coding:

        try:
            return ask_openai(question, live=live)

        except Exception:

            # Gemini fallback
            return ask_gemini(question, live=live)


    # -----------------------------------------------------
    # 3️⃣ Live/current → Gemini with Google Search
    # -----------------------------------------------------

    if live:

        try:
            return ask_gemini(question, live=True)

        except Exception:

            # OpenAI fallback
            return ask_openai(question, live=True)


    # -----------------------------------------------------
    # 4️⃣ Normal question → OpenAI first
    # -----------------------------------------------------

    try:
        return ask_openai(question, live=False)

    except Exception:

        # Gemini fallback
        return ask_gemini(question, live=False)


# =========================================================
# 🏠 HOME
# =========================================================

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "status": "success",
        "title": "🦅 PHOENIX AI",
        "data": "Phoenix AI V2 Backend is Active!"
    })


# =========================================================
# ❤️ HEALTH CHECK
# =========================================================

@app.route("/health", methods=["GET"])
def health():

    return jsonify({
        "status": "success",
        "openai": bool(openai_client),
        "gemini": bool(gemini_client),
        "openai_model": OPENAI_MODEL,
        "gemini_model": GEMINI_MODEL
    })


# =========================================================
# 🚀 MAIN AI ROUTE
# =========================================================

@app.route("/run", methods=["GET", "POST"])
def run_ai():

    try:

        user_query = ""

        # GET
        user_query = request.args.get("query", "").strip()

        # POST JSON
        if not user_query and request.is_json:

            data = request.get_json(silent=True) or {}

            user_query = (
                data.get("prompt")
                or data.get("query")
                or data.get("message")
                or ""
            ).strip()

        # Empty question
        if not user_query:

            return jsonify({
                "status": "success",
                "title": "🦅 PHOENIX AI",
                "data": "నమస్తే! 🦅 నేను Phoenix AI. ఏదైనా అడుగు."
            })


        # -------------------------------------------------
        # AI ENGINE
        # -------------------------------------------------

        answer = phoenix_engine(user_query)


        # -------------------------------------------------
        # FINAL RESPONSE
        # -------------------------------------------------

        return jsonify({
            "status": "success",
            "title": "🦅 PHOENIX AI",
            "data": answer
        })


    except Exception as e:

        return jsonify({
            "status": "error",
            "title": "🦅 PHOENIX AI ERROR",
            "data": f"సమస్య: {str(e)}"
        }), 500


# =========================================================
# 🚀 RENDER START
# =========================================================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
