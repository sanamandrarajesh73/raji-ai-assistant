import os
import re
import json
import urllib.request
import urllib.error

from flask import Flask, request, jsonify
from flask_cors import CORS

from google import genai
from google.genai import types


# =========================================================
# 🦅 PHOENIX AI
# =========================================================

app = Flask(__name__)
CORS(app)


# =========================================================
# 🔐 ENVIRONMENT VARIABLES
# =========================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

TENNIS_API_KEY = os.getenv("TENNIS_API_KEY")

TENNIS_BASE_URL = (
    "https://api.livetennisapi.com/api/public/v1"
)


# =========================================================
# 🤖 GEMINI CLIENT
# =========================================================

gemini_client = None

if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(
            api_key=GEMINI_API_KEY
        )
        print("🦅 Gemini client READY")
    except Exception as e:
        print("Gemini client error:", str(e))


# =========================================================
# 🧠 PHOENIX SYSTEM
# =========================================================

PHOENIX_INSTRUCTIONS = """
You are PHOENIX AI.

Creator: Rajesh.

You are a friendly, practical and intelligent AI assistant.

The user may ask about:
- General knowledge
- Education
- Coding
- Technology
- AI
- English
- Finance education
- Sports
- Tennis
- Cricket
- Stocks
- Latest information

Answer in simple Telugu when the user asks in Telugu.

If the user asks in English, answer in English.

For mixed Telugu-English questions, naturally use both.

Be honest.
Do not invent live information.
Do not claim guaranteed predictions.

For sports predictions:
Give analysis based on the available current information.
Never say a player is guaranteed to win.

Avoid unnecessary Markdown formatting.
"""


# =========================================================
# 🧹 CLEAN RESPONSE
# =========================================================

def clean_response(text):

    if not text:
        return "సమాధానం రాలేదు."

    text = str(text).strip()

    text = text.replace("**", "")
    text = text.replace("__", "")

    text = re.sub(
        r"(?m)^\s*#{1,6}\s*",
        "",
        text
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# =========================================================
# 🤖 GEMINI
# =========================================================

def ask_gemini(user_message):

    if not gemini_client:
        return (
            "PHOENIX AIకి Gemini కనెక్షన్ లేదు."
        )

    try:

        response = gemini_client.models.generate_content(

            model=GEMINI_MODEL,

            contents=user_message,

            config=types.GenerateContentConfig(

                system_instruction=PHOENIX_INSTRUCTIONS,

                temperature=0.7,

                max_output_tokens=2048
            )
        )

        if response and response.text:

            return clean_response(
                response.text
            )

        return "PHOENIXకి సమాధానం రాలేదు."

    except Exception as e:

        print(
            "Gemini error:",
            str(e)
        )

        return (
            "PHOENIX AI ప్రస్తుతం అందుబాటులో లేదు."
        )


# =========================================================
# 🌐 TENNIS API REQUEST
# =========================================================

def tennis_request(endpoint):

    if not TENNIS_API_KEY:

        return {
            "ok": False,
            "error": "TENNIS_API_KEY_MISSING"
        }


    url = TENNIS_BASE_URL + endpoint


    headers = {
        "X-API-Key": TENNIS_API_KEY,
        "Accept": "application/json",
        "User-Agent": "PHOENIX-AI/1.0"
    }


    req = urllib.request.Request(
        url,
        headers=headers,
        method="GET"
    )


    try:

        with urllib.request.urlopen(
            req,
            timeout=15
        ) as response:

            raw = response.read().decode(
                "utf-8"
            )

            data = json.loads(raw)

            return {
                "ok": True,
                "data": data
            }


    except urllib.error.HTTPError as e:

        body = ""

        try:
            body = e.read().decode(
                "utf-8"
            )
        except:
            pass

        print(
            "Tennis HTTP error:",
            e.code,
            body
        )

        return {
            "ok": False,
            "status_code": e.code,
            "error": body or str(e)
        }


    except Exception as e:

        print(
            "Tennis connection error:",
            str(e)
        )

        return {
            "ok": False,
            "error": str(e)
        }


# =========================================================
# 🎾 PLAYER NAME HELPER
# =========================================================

def get_player_name(player):

    if not player:
        return "Unknown"

    if isinstance(player, str):
        return player

    if isinstance(player, dict):

        for key in [
            "name",
            "full_name",
            "display_name"
        ]:

            value = player.get(key)

            if value:
                return str(value)

        first = player.get("first_name", "")
        last = player.get("last_name", "")

        name = (
            str(first) + " " + str(last)
        ).strip()

        if name:
            return name

    return "Unknown"


# =========================================================
# 🎾 EXTRACT PLAYERS
# =========================================================

def extract_players(match):

    players = match.get(
        "players",
        {}
    )

    p1 = None
    p2 = None


    if isinstance(players, dict):

        p1 = (
            players.get("p1")
            or players.get("player1")
            or players.get("1")
        )

        p2 = (
            players.get("p2")
            or players.get("player2")
            or players.get("2")
        )


    elif isinstance(players, list):

        if len(players) > 0:
            p1 = players[0]

        if len(players) > 1:
            p2 = players[1]


    return (
        get_player_name(p1),
        get_player_name(p2)
    )


# =========================================================
# 🎾 SCORE FORMAT
# =========================================================

def format_sets(sets):

    if not sets:
        return "Score unavailable"

    try:

        return "  ".join(
            f"{s[0]}-{s[1]}"
            for s in sets
            if isinstance(s, list)
            and len(s) >= 2
        )

    except:

        return str(sets)


# =========================================================
# 🎾 WINNER ANALYSIS
# =========================================================

def estimate_leader(match):

    score = match.get(
        "score"
    ) or {}

    sets = score.get(
        "sets"
    ) or []

    if not sets:
        return (
            "ప్రస్తుతం winner prediction ఇవ్వడానికి "
            "తగిన score లేదు."
        )


    p1, p2 = extract_players(
        match
    )


    p1_sets = 0
    p2_sets = 0


    try:

        for s in sets:

            if (
                isinstance(s, list)
                and len(s) >= 2
            ):

                if s[0] > s[1]:
                    p1_sets += 1

                elif s[1] > s[0]:
                    p2_sets += 1

    except:
        pass


    if p1_sets > p2_sets:

        return (
            f"ప్రస్తుతం {p1} ముందంజలో ఉన్నారు. "
            f"Live score ఆధారంగా {p1}కి advantage ఉంది."
        )


    if p2_sets > p1_sets:

        return (
            f"ప్రస్తుతం {p2} ముందంజలో ఉన్నారు. "
            f"Live score ఆధారంగా {p2}కి advantage ఉంది."
        )


    return (
        "ఇద్దరూ ప్రస్తుతం సమానంగా ఉన్నారు. "
        "Match close గా ఉంది."
    )


# =========================================================
# 🎾 LIVE TENNIS
# =========================================================

def get_live_tennis():

    result = tennis_request(
        "/matches?status=live&limit=50"
    )


    if not result.get("ok"):

        return {
            "ok": False,
            "message": (
                "🎾 Tennis Live API కనెక్ట్ కాలేదు."
            ),
            "details": result
        }


    payload = result.get(
        "data",
        {}
    )


    matches = payload.get(
        "data",
        []
    )


    if not matches:

        return {
            "ok": True,
            "matches": [],
            "message": (
                "🎾 ప్రస్తుతం Live Tennis matches "
                "కనిపించడం లేదు."
            )
        }


    output = []


    for match in matches:

        p1, p2 = extract_players(
            match
        )


        score = match.get(
            "score"
        ) or {}


        sets = score.get(
            "sets"
        ) or []


        games = score.get(
            "games"
        )


        points = score.get(
            "points"
        )


        server = score.get(
            "server"
        )


        output.append({

            "id": match.get("id"),

            "tournament": match.get(
                "tournament"
            ),

            "tour": match.get(
                "tour"
            ),

            "surface": match.get(
                "surface"
            ),

            "round": match.get(
                "round"
            ),

            "status": match.get(
                "status"
            ),

            "event_status": match.get(
                "event_status"
            ),

            "player1": p1,

            "player2": p2,

            "sets": sets,

            "games": games,

            "points": points,

            "server": server,

            "score_text": format_sets(
                sets
            ),

            "stale": score.get(
                "stale"
            ),

            "age_seconds": score.get(
                "age_seconds"
            ),

            "leader_analysis":
                estimate_leader(match)
        })


    return {

        "ok": True,

        "count": len(output),

        "matches": output

    }


# =========================================================
# 🎾 TENNIS RESPONSE FOR USER
# =========================================================

def tennis_text_response():

    data = get_live_tennis()


    if not data.get("ok"):

        return (
            "🎾 PHOENIX Tennis Live\n\n"
            + data.get(
                "message",
                "Tennis data unavailable."
            )
        )


    matches = data.get(
        "matches",
        []
    )


    if not matches:

        return data.get(
            "message",
            "🎾 ప్రస్తుతం Live matches లేవు."
        )


    lines = [

        "🎾 PHOENIX LIVE TENNIS",

        f"Live Matches: {len(matches)}",

        ""
    ]


    for index, match in enumerate(
        matches,
        start=1
    ):

        lines.append(
            f"🎾 Match {index}"
        )

        lines.append(
            f"👤 {match['player1']} vs "
            f"{match['player2']}"
        )


        if match.get("tournament"):

            lines.append(
                f"🏆 {match['tournament']}"
            )


        if match.get("tour"):

            lines.append(
                f"🌐 Tour: {match['tour']}"
            )


        lines.append(
            f"🔢 Score: {match['score_text']}"
        )


        if match.get("games"):

            lines.append(
                f"🎯 Games: {match['games']}"
            )


        if match.get("points"):

            lines.append(
                f"🎾 Points: {match['points']}"
            )


        if match.get("server"):

            server_name = (
                match["player1"]
                if match["server"] == 1
                else match["player2"]
            )

            lines.append(
                f"🏓 Server: {server_name}"
            )


        lines.append(
            "📊 "
            + match["leader_analysis"]
        )


        lines.append("")


    lines.append(
        "ℹ️ Score is from the live tennis data feed."
    )

    return "\n".join(lines)


# =========================================================
# 🎯 TENNIS QUESTION DETECTOR
# =========================================================

def is_tennis_query(text):

    text = text.lower()


    keywords = [

        "tennis",
        "టెన్నిస్",

        "atp",
        "wta",

        "sinner",
        "alcaraz",
        "djokovic",
        "nadal",

        "swiatek",
        "sabalenka",
        "gauff",

        "live score",
        "live match",

        "టెన్నిస్ స్కోర్",
        "టెన్నిస్ మ్యాచ్",

        "ఎవరు గెలుస్తారు",
        "ఎవరు గెలిచారు"

    ]


    return any(
        keyword in text
        for keyword in keywords
    )


# =========================================================
# ❤️ HEALTH
# =========================================================

@app.route(
    "/health",
    methods=["GET"]
)
def health():

    return jsonify({

        "status": "ok",

        "service": "PHOENIX AI",

        "gemini":
            "connected"
            if gemini_client
            else "not_configured",

        "tennis":
            "connected"
            if TENNIS_API_KEY
            else "not_configured",

        "model":
            GEMINI_MODEL

    })


# =========================================================
# 🎾 DIRECT TENNIS API
# =========================================================

@app.route(
    "/tennis/live",
    methods=["GET"]
)
def tennis_live_route():

    data = get_live_tennis()


    if not data.get("ok"):

        return jsonify({

            "status": "error",

            "title": "🎾 PHOENIX LIVE TENNIS",

            "data": data

        }), 500


    return jsonify({

        "status": "success",

        "title": "🎾 PHOENIX LIVE TENNIS",

        "data": data

    })


# =========================================================
# 🧠 MAIN PHOENIX ROUTER
# =========================================================

@app.route(
    "/run",
    methods=["GET", "POST"]
)
def run_query():

    try:

        query = ""


        if request.method == "GET":

            query = request.args.get(
                "query",
                ""
            )


        elif request.method == "POST":

            body = request.get_json(
                silent=True
            ) or {}

            query = body.get(
                "query",
                ""
            )

            if not query:

                query = request.args.get(
                    "query",
                    ""
                )


        query = str(
            query
        ).strip()


        if not query:

            return jsonify({

                "status": "error",

                "title": "🦅 PHOENIX AI",

                "data":
                    "దయచేసి మీ ప్రశ్నను పంపండి."

            }), 400


        print(
            "PHOENIX QUERY:",
            query
        )


        # =================================================
        # 🎾 TENNIS ROUTER
        # =================================================

        if is_tennis_query(query):

            answer = tennis_text_response()


            return jsonify({

                "status": "success",

                "title":
                    "🎾 PHOENIX LIVE TENNIS",

                "data": answer

            })


        # =================================================
        # 🧠 NORMAL AI
        # =================================================

        answer = ask_gemini(
            query
        )


        return jsonify({

            "status": "success",

            "title":
                "🦅 PHOENIX AI",

            "data": answer

        })


    except Exception as e:

        print(
            "RUN ERROR:",
            str(e)
        )


        return jsonify({

            "status": "error",

            "title":
                "🦅 PHOENIX AI",

            "data":
                "PHOENIX server error వచ్చింది."

        }), 500


# =========================================================
# 🏠 HOME
# =========================================================

@app.route(
    "/",
    methods=["GET"]
)
def home():

    return """
    🦅 PHOENIX AI Backend

    Status: ONLINE

    AI: READY

    Tennis Live: READY

    Endpoints:
    /run
    /tennis/live
    /health
    """


# =========================================================
# 🚀 START
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )


    print(
        "==================================="
    )

    print(
        "🦅 PHOENIX AI SERVER"
    )

    print(
        "Port:",
        port
    )

    print(
        "Gemini:",
        bool(GEMINI_API_KEY)
    )

    print(
        "Tennis:",
        bool(TENNIS_API_KEY)
    )

    print(
        "==================================="
    )


    app.run(
        host="0.0.0.0",
        port=port
    )
