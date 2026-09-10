import os
from flask import Flask, request, jsonify
from flask_cors import CORS

from openai import OpenAI
from google import genai
from google.genai import types


# =========================================================
# 🦅 PHOENIX AI V3
# Gemini Primary + OpenAI Optional
# Smart Router + Live Search + Automatic Fallback
# =========================================================

app = Flask(__name__)
CORS(app)


# =========================================================
# 🔐 API KEYS
# =========================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


# =========================================================
# 🤖 CLIENTS
# =========================================================

openai_client = None
gemini_client = None


if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(
            api_key=OPENAI_API_KEY
        )
    except Exception:
        openai_client = None


if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(
            api_key=GEMINI_API_KEY
        )
    except Exception:
        gemini_client = None


# =========================================================
# 🧠 MODEL SETTINGS
# =========================================================

OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-4.1"
)

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash"
)


# =========================================================
# 🦅 PHOENIX PERSONALITY
# =========================================================

PHOENIX_INSTRUCTIONS = """
You are PHOENIX AI.

Creator: Rajesh

You are an advanced all-round AI assistant.

Main goals:

1. Give accurate and useful answers.
2. Think carefully before answering.
3. Never invent facts.
4. For current information, use live search when available.
5. Clearly separate facts, estimates and opinions.
6. If uncertain, say so honestly.
7. If the user speaks Telugu, answer in fluent and simple Telugu.
8. If the user asks for English, answer in English.
9. Help with coding, technology, education, science,
   finance, business, productivity and general knowledge.
10. For coding problems, provide practical working solutions.
11. Never expose API keys or secret credentials.
12. Never claim 100% accuracy or guaranteed future results.
13. Be concise but useful.
14. Give the direct answer first.
"""


# =========================================================
# 🔎 LIVE INFORMATION DETECTION
# =========================================================

def needs_live_information(text):

    keywords = [
        "today",
        "latest",
        "live",
        "now",
        "current",
        "news",
        "price",
        "stock price",
        "weather",
        "score",
        "match",
        "market",

        "ఈరోజు",
        "ఇప్పుడు",
        "తాజా",
        "లైవ్",
        "ప్రస్తుతం",
        "నేటి",
        "ఇప్పటి",
        "వార్తలు",
        "ధర",
        "స్కోర్",
        "మ్యాచ్",
        "మార్కెట్"
    ]

    text_lower = text.lower()

    return any(
        word.lower() in text_lower
        for word in keywords
    )


# =========================================================
# 💻 CODING DETECTION
# =========================================================

def is_coding_question(text):

    keywords = [
        "python",
        "javascript",
        "java",
        "flutter",
        "kodular",
        "android",
        "api",
        "flask",
        "code",
        "coding",
        "bug",
        "error",
        "github",
        "render",

        "కోడింగ్",
        "కోడ్",
        "ఎర్రర్",
        "బగ్"
    ]

    text_lower = text.lower()

    return any(
        word.lower() in text_lower
        for word in keywords
    )


# =========================================================
# 🧠 DEEP QUESTION DETECTION
# =========================================================

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
        "ఎలా తయారు",
        "లోతుగా"
    ]

    text_lower = text.lower()

    return any(
        word.lower() in text_lower
        for word in keywords
    )


# =========================================================
# 💎 GEMINI ENGINE
# =========================================================

def ask_gemini(question, live=False):

    if not gemini_client:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    tools = []

    # Google Search for current information
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

    # Primary model
    models_to_try = [
        GEMINI_MODEL,
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash"
    ]

    # Remove duplicates
    models_to_try = list(
        dict.fromkeys(models_to_try)
    )

    last_error = None

    for model_name in models_to_try:

        try:

            response = gemini_client.models.generate_content(
                model=model_name,
                contents=question,
                config=config
            )

            if response and response.text:

                return response.text.strip()

        except Exception as e:

            last_error = e
            continue

    raise RuntimeError(
        f"Gemini unavailable: {str(last_error)}"
    )


# =========================================================
# 🤖 OPENAI ENGINE
# =========================================================

def ask_openai(question, live=False):

    if not openai_client:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured."
        )

    tools = []

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

    if not response.output_text:

        raise RuntimeError(
            "OpenAI returned an empty response."
        )

    return response.output_text.strip()


# =========================================================
# 🧠 GEMINI SYNTHESIS
# =========================================================

def synthesize_with_gemini(
    question,
    answer_a,
    answer_b
):

    synthesis_prompt = f"""
You are the final Phoenix AI answer engine.

User question:
{question}

Answer A:
{answer_a}

Answer B:
{answer_b}

Create ONE reliable final answer.

Rules:

- Compare both answers.
- Remove obvious contradictions.
- Do not invent missing facts.
- If information is uncertain, say so.
- Give the direct answer first.
- Then explain briefly.
- If the user speaks Telugu, answer in Telugu.
- Keep the answer clear and useful.
"""

    return ask_gemini(
        synthesis_prompt,
        live=False
    )


# =========================================================
# 🧭 PHOENIX SMART ROUTER
# =========================================================

def phoenix_engine(question):

    live = needs_live_information(question)
    coding = is_coding_question(question)
    deep = needs_deep_reasoning(question)


    # =====================================================
    # 1️⃣ DEEP QUESTION
    # =====================================================

    if deep:

        gemini_answer = None
        openai_answer = None


        # Gemini first
        try:

            gemini_answer = ask_gemini(
                question,
                live=live
            )

        except Exception as e:

            gemini_answer = None


        # OpenAI optional
        if openai_client:

            try:

                openai_answer = ask_openai(
                    question,
                    live=live
                )

            except Exception:

                openai_answer = None


        # Both available
        if gemini_answer and openai_answer:

            try:

                return synthesize_with_gemini(
                    question,
                    gemini_answer,
                    openai_answer
                )

            except Exception:

                return gemini_answer


        # Gemini available
        if gemini_answer:

            return gemini_answer


        # OpenAI available
        if openai_answer:

            return openai_answer


        raise RuntimeError(
            "Both AI services are currently unavailable."
        )


    # =====================================================
    # 2️⃣ LIVE QUESTION
    # =====================================================

    if live:

        # Gemini + Google Search FIRST

        try:

            return ask_gemini(
                question,
                live=True
            )

        except Exception:

            pass


        # OpenAI optional fallback

        if openai_client:

            try:

                return ask_openai(
                    question,
                    live=True
                )

            except Exception:

                pass


        raise RuntimeError(
            "Live AI services are currently unavailable."
        )


    # =====================================================
    # 3️⃣ CODING QUESTION
    # =====================================================

    if coding:

        # Gemini first

        try:

            return ask_gemini(
                question,
                live=False
            )

        except Exception:

            pass


        # OpenAI optional fallback

        if openai_client:

            try:

                return ask_openai(
                    question,
                    live=False
                )

            except Exception:

                pass


        raise RuntimeError(
            "Coding AI services are currently unavailable."
        )


    # =====================================================
    # 4️⃣ NORMAL QUESTION
    # =====================================================

    # Gemini FIRST
    try:

        return ask_gemini(
            question,
            live=False
        )

    except Exception:

        pass


    # OpenAI SECOND
    if openai_client:

        try:

            return ask_openai(
                question,
                live=False
            )

        except Exception:

            pass


    raise RuntimeError(
        "Phoenix AI services are currently unavailable."
    )


# =========================================================
# 🏠 HOME
# =========================================================

@app.route("/", methods=["GET"])
def home():

    return jsonify({

        "status": "success",

        "title": "🦅 PHOENIX AI",

        "data":
        "Phoenix AI V3 Backend is Active!"
    })


# =========================================================
# ❤️ HEALTH CHECK
# =========================================================

@app.route("/health", methods=["GET"])
def health():

    return jsonify({

        "status": "success",

        "gemini": bool(gemini_client),

        "openai": bool(openai_client),

        "gemini_model": GEMINI_MODEL,

        "openai_model": OPENAI_MODEL,

        "engine":
        "Gemini Primary + OpenAI Optional"
    })


# =========================================================
# 🚀 MAIN AI ROUTE
# =========================================================

@app.route(
    "/run",
    methods=["GET", "POST"]
)
def run_ai():

    try:

        user_query = ""


        # =================================================
        # GET
        # =================================================

        user_query = request.args.get(
            "query",
            ""
        ).strip()


        # =================================================
        # POST JSON
        # =================================================

        if not user_query and request.is_json:

            data = request.get_json(
                silent=True
            ) or {}

            user_query = (

                data.get("prompt")

                or data.get("query")

                or data.get("message")

                or ""

            ).strip()


        # =================================================
        # EMPTY QUESTION
        # =================================================

        if not user_query:

            return jsonify({

                "status": "success",

                "title":
                "🦅 PHOENIX AI",

                "data":
                "నమస్తే! 🦅 నేను Phoenix AI. ఏదైనా అడుగు."
            })


        # =================================================
        # AI
        # =================================================

        answer = phoenix_engine(
            user_query
        )


        # =================================================
        # FINAL RESPONSE
        # =================================================

        return jsonify({

            "status": "success",

            "title":
            "🦅 PHOENIX AI",

            "data":
            answer
        })


    except Exception as e:

        return jsonify({

            "status": "error",

            "title":
            "🦅 PHOENIX AI ERROR",

            "data":
            "ప్రస్తుతం Phoenix AIకి AI serviceలో సమస్య ఉంది. "
            "కొద్దిసేపటి తర్వాత మళ్లీ ప్రయత్నించండి."

        }), 500


# =========================================================
# 🚀 RENDER START
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
)
