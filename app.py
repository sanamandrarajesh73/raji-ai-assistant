import os
import re

from flask import Flask, request, jsonify
from flask_cors import CORS

from openai import OpenAI
from google import genai
from google.genai import types


# =========================================================
# 🦅 PHOENIX AI
# Gemini Primary + OpenAI Optional
# Clean Answers + Live Search + Smart Understanding
# =========================================================

app = Flask(__name__)
CORS(app)


# =========================================================
# 🔐 API KEYS
# =========================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


# =========================================================
# 🤖 AI CLIENTS
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
# 🦅 PHOENIX AI INSTRUCTIONS
# =========================================================

PHOENIX_INSTRUCTIONS = """
You are PHOENIX AI.

Creator: Rajesh.

You are an advanced all-round AI assistant.

Your most important job is to understand what the user
actually wants before answering.

GENERAL RULES:

1. Understand the complete user question and its intent.
2. Do not answer based on only one keyword.
3. Answer the actual question the user asked.
4. If the question is simple, give a simple answer.
5. If the user wants detailed information, give a detailed answer.
6. If the user speaks Telugu, answer naturally in clear and simple Telugu.
7. If the user mixes Telugu and English, understand both.
8. If the user asks in English, answer in English.
9. Do not unnecessarily repeat the user's question.
10. Do not give unrelated information.
11. Be helpful, practical and honest.
12. Never invent facts.
13. If information is uncertain, clearly say that it is uncertain.
14. For current information, use live search when available.
15. For stock market questions, clearly separate current facts,
    analysis, estimates and predictions.
16. Never invent live stock prices, news, scores or market data.
17. For coding questions, provide practical working solutions.
18. Explain difficult technical topics in beginner-friendly language.
19. Help with education, science, technology, programming,
    finance, business, productivity and general knowledge.
20. Never expose API keys, passwords or secret credentials.
21. Never claim guaranteed profits or 100 percent accuracy.

IMPORTANT RESPONSE STYLE:

The answer must be clean and easy to read on a mobile phone.

DO NOT use Markdown formatting.

DO NOT use:

**
###
##
__text__
---

Do not put unnecessary symbols around words.

You MAY use:

1. Numbered points
2. Numbered steps
• Simple bullet points

Use normal paragraphs when appropriate.

The final answer should look like a clean professional AI assistant
response, not like raw Markdown.
"""


# =========================================================
# 🧹 CLEAN AI RESPONSE
# =========================================================

def clean_response(text):

    if not text:
        return "క్షమించండి, ప్రస్తుతం సమాధానం అందుబాటులో లేదు."

    text = str(text)

    # Remove Markdown bold and italic markers
    text = text.replace("**", "")
    text = text.replace("__", "")

    # Remove Markdown headings
    text = re.sub(
        r"(?m)^\s*#{1,6}\s*",
        "",
        text
    )

    # Remove code fence markers
    text = text.replace("```python", "")
    text = text.replace("```javascript", "")
    text = text.replace("```typescript", "")
    text = text.replace("```java", "")
    text = text.replace("```json", "")
    text = text.replace("```html", "")
    text = text.replace("```css", "")
    text = text.replace("```bash", "")
    text = text.replace("```text", "")
    text = text.replace("```", "")

    # Convert Markdown bullets to clean bullets
    text = re.sub(
        r"(?m)^\s*[-*]\s+",
        "• ",
        text
    )

    # Remove horizontal separators
    text = re.sub(
        r"(?m)^\s*-{3,}\s*$",
        "",
        text
    )

    # Remove excessive blank lines
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


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
        "share price",
        "weather",
        "score",
        "match",
        "market",
        "result",
        "results",
        "update",
        "updates",

        "ఈరోజు",
        "ఇప్పుడు",
        "తాజా",
        "లైవ్",
        "ప్రస్తుతం",
        "నేటి",
        "ఇప్పటి",
        "వార్తలు",
        "ధర",
        "షేర్ ధర",
        "స్టాక్ ధర",
        "స్కోర్",
        "మ్యాచ్",
        "మార్కెట్",
        "రిజల్ట్",
        "అప్డేట్",
        "అప్‌డేట్"
    ]

    text_lower = text.lower()

    return any(
        word.lower() in text_lower
        for word in keywords
    )


# =========================================================
# 💻 CODING QUESTION DETECTION
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
        "html",
        "css",
        "json",
        "database",
        "programming",

        "కోడింగ్",
        "కోడ్",
        "ఎర్రర్",
        "బగ్",
        "ప్రోగ్రామింగ్"
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
        "comparison",
        "analysis",
        "analyze",
        "strategy",
        "architecture",
        "why",
        "how to build",
        "advantages",
        "disadvantages",
        "difference",

        "పూర్తిగా",
        "విశ్లేషణ",
        "పోల్చి",
        "పోలిక",
        "ఎందుకు",
        "ఎలా తయారు",
        "లోతుగా",
        "ప్రయోజనాలు",
        "నష్టాలు",
        "తేడా"
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

    models_to_try = [
        GEMINI_MODEL,
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash"
    ]

    # Remove duplicate model names
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

                return clean_response(
                    response.text
                )

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

    return clean_response(
        response.output_text
    )


# =========================================================
# 🧠 PHOENIX SMART ROUTER
# =========================================================

def phoenix_engine(question):

    live = needs_live_information(question)

    coding = is_coding_question(question)

    deep = needs_deep_reasoning(question)


    # =====================================================
    # 1. CURRENT / LIVE QUESTIONS
    # =====================================================

    if live:

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


    # =====================================================
    # 2. CODING QUESTIONS
    # =====================================================

    if coding:

        try:

            return ask_gemini(
                question,
                live=False
            )

        except Exception:

            pass


        if openai_client:

            try:

                return ask_openai(
                    question,
                    live=False
                )

            except Exception:

                pass


    # =====================================================
    # 3. DEEP QUESTIONS
    # =====================================================

    if deep:

        try:

            return ask_gemini(
                question,
                live=live
            )

        except Exception:

            pass


        if openai_client:

            try:

                return ask_openai(
                    question,
                    live=live
                )

            except Exception:

                pass


    # =====================================================
    # 4. NORMAL QUESTIONS
    # =====================================================

    try:

        return ask_gemini(
            question,
            live=False
        )

    except Exception:

        pass


    # =====================================================
    # 5. OPENAI OPTIONAL FALLBACK
    # =====================================================

    if openai_client:

        try:

            return ask_openai(
                question,
                live=False
            )

        except Exception:

            pass


    # =====================================================
    # 6. FINAL ERROR
    # =====================================================

    raise RuntimeError(
        "Phoenix AI services are currently unavailable."
    )


# =========================================================
# 🏠 HOME
# =========================================================

@app.route(
    "/",
    methods=["GET"]
)
def home():

    return jsonify({

        "status": "success",

        "title": "🦅 PHOENIX AI",

        "data":
        "Phoenix AI is Active!"
    })


# =========================================================
# ❤️ HEALTH CHECK
# =========================================================

@app.route(
    "/health",
    methods=["GET"]
)
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
# 🚀 MAIN AI FUNCTION
# =========================================================

def process_ai_request():

    try:

        user_query = ""


        # =================================================
        # GET REQUEST
        # =================================================

        user_query = request.args.get(
            "query",
            ""
        ).strip()


        # =================================================
        # POST JSON REQUEST
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
        # EMPTY MESSAGE
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
        # AI ENGINE
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
            clean_response(answer)
        })


    except Exception as e:

        print(
            "PHOENIX ERROR:",
            str(e)
        )

        return jsonify({

            "status": "error",

            "title":
            "🦅 PHOENIX AI ERROR",

            "data":
            "క్షమించండి. ప్రస్తుతం Phoenix AI serviceలో సమస్య ఉంది. కొద్దిసేపటి తర్వాత మళ్లీ ప్రయత్నించండి."

        }), 500


# =========================================================
# 🚀 /run
# =========================================================

@app.route(
    "/run",
    methods=["GET", "POST"]
)
def run_ai():

    return process_ai_request()


# =========================================================
# 🚀 /chat
# =========================================================

@app.route(
    "/chat",
    methods=["GET", "POST"]
)
def chat_ai():

    return process_ai_request()


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
