import os
import re
import json
import time
import math
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

from flask import Flask, request, jsonify
from flask_cors import CORS

from google import genai
from google.genai import types


# =========================================================
# PHOENIX AI BACKEND
# =========================================================

app = Flask(__name__)
CORS(app)


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash"
).strip()

TENNIS_API_KEY = os.getenv(
    "TENNIS_API_KEY",
    ""
).strip()

ENABLE_WEB_SEARCH = os.getenv(
    "ENABLE_WEB_SEARCH",
    "true"
).lower() == "true"


TENNIS_BASE_URL = (
    "https://api.livetennisapi.com/api/public/v1"
)


# =========================================================
# GEMINI CLIENT
# =========================================================

gemini_client = None

if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(
            api_key=GEMINI_API_KEY
        )
        print("PHOENIX: Gemini client ready")
    except Exception as e:
        print("PHOENIX: Gemini client error:", e)


# =========================================================
# PHOENIX SYSTEM INSTRUCTIONS
# =========================================================

PHOENIX_INSTRUCTIONS = """
You are PHOENIX AI.

Creator: Rajesh.

You are a friendly, intelligent mobile AI assistant.

Important rules:

1. Understand the user's complete question before answering.
2. Answer in simple Telugu when the user speaks Telugu.
3. If the user asks in English, answer in simple English unless Telugu explanation is useful.
4. For current/latest/today/news questions, use live web search when available.
5. Never pretend old knowledge is current.
6. If information is uncertain, clearly say that it is uncertain.
7. For sports, do not invent scores or results.
8. For finance, clearly separate facts, analysis and estimates.
9. Keep answers mobile-friendly.
10. Do not use unnecessary Markdown decorations.
11. Do not use repeated asterisks.
12. Do not use huge headings.
13. Be direct and useful.
14. Never claim an estimated sports probability is official unless the API provides an official probability.
"""


# =========================================================
# RESPONSE CLEANER
# =========================================================

def clean_response(text):
    if not text:
        return "PHOENIX: No response received."

    text = str(text).strip()

    # Remove common markdown decoration
    text = text.replace("**", "")
    text = text.replace("__", "")
    text = text.replace("###", "")
    text = text.replace("##", "")
    text = text.replace("---", "")

    # Remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# =========================================================
# WEB QUERY DETECTION
# =========================================================

def is_web_query(query):
    q = query.lower().strip()

    web_words = [
        "latest",
        "today",
        "current",
        "now",
        "news",
        "recent",
        "update",
        "updates",
        "live news",
        "tv9",
        "tv9 ap",
        "tv9 telugu",
        "andhra pradesh",
        "andhra",
        "ap news",
        "telugu news",
        "breaking news",
        "ఈరోజు",
        "ఇప్పుడు",
        "తాజా",
        "వార్తలు",
        "న్యూస్",
        "లేటెస్ట్",
        "ప్రస్తుతం",
        "అప్డేట్",
        "ఏం జరిగింది",
        "ఏం జరుగుతోంది"
    ]

    return any(word in q for word in web_words)


# =========================================================
# TENNIS QUERY DETECTION
# =========================================================

def is_tennis_query(query):
    q = query.lower().strip()

    tennis_words = [
        "tennis",
        "tennis match",
        "live tennis",
        "tennis live",
        "tennis score",
        "tennis scores",
        "atp",
        "wta",
        "itf",
        "challenger",
        "grand slam",
        "wimbledon",
        "roland garros",
        "french open",
        "us open",
        "australian open",
        "serve",
        "set score",
        "tennis player",
        "టెన్నిస్",
        "టెన్నిస్ మ్యాచ్",
        "టెన్నిస్ స్కోర్",
        "లైవ్ టెన్నిస్",
        "టెన్నిస్ ఎవరు",
    ]

    return any(word in q for word in tennis_words)


# =========================================================
# GEMINI AI
# =========================================================

def ask_gemini(user_message, use_web=False):

    if gemini_client is None:
        return (
            "PHOENIX Error:\n"
            "GEMINI_API_KEY Render Environment Variables లో లేదు."
        )

    last_error = None

    for attempt in range(2):

        try:

            config_kwargs = {
                "system_instruction": PHOENIX_INSTRUCTIONS,
                "temperature": 0.7,
                "max_output_tokens": 2048,
            }

            # Google Search grounding
            if use_web and ENABLE_WEB_SEARCH:
                config_kwargs["tools"] = [
                    types.Tool(
                        google_search=types.GoogleSearch()
                    )
                ]

            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=user_message,
                config=types.GenerateContentConfig(
                    **config_kwargs
                )
            )

            if response and response.text:
                return clean_response(response.text)

            last_error = "Empty Gemini response."

        except Exception as e:

            last_error = str(e)

            print(
                f"Gemini attempt {attempt + 1} failed: "
                f"{last_error}"
            )

            time.sleep(1)

    return (
        "PHOENIX AI ప్రస్తుతం response ఇవ్వలేకపోయింది.\n"
        "కొద్దిసేపటి తర్వాత మళ్లీ try చేయండి."
    )


# =========================================================
# TENNIS API REQUEST
# =========================================================

def tennis_request(endpoint):

    if not TENNIS_API_KEY:
        return {
            "error": "TENNIS_API_KEY Render Environment Variables లో లేదు."
        }

    url = TENNIS_BASE_URL + endpoint

    request_obj = urllib.request.Request(
        url,
        headers={
            "X-API-Key": TENNIS_API_KEY,
            "Accept": "application/json",
            "User-Agent": "PHOENIX-AI/1.0"
        },
        method="GET"
    )

    try:

        with urllib.request.urlopen(
            request_obj,
            timeout=15
        ) as response:

            raw = response.read().decode("utf-8")

            return json.loads(raw)

    except urllib.error.HTTPError as e:

        try:
            body = e.read().decode("utf-8")
        except:
            body = ""

        print(
            "Tennis API HTTP Error:",
            e.code,
            body
        )

        return {
            "error": f"Tennis API HTTP {e.code}",
            "details": body
        }

    except Exception as e:

        print(
            "Tennis API error:",
            str(e)
        )

        return {
            "error": str(e)
        }


# =========================================================
# TEXT / NUMBER HELPERS
# =========================================================

def safe_int(value, default=0):

    try:
        return int(value)
    except:
        return default


def clean_name(value):

    if value is None:
        return "Unknown"

    return str(value).strip()


# =========================================================
# PLAYER / TEAM NAMES
# =========================================================

def get_player_names(match):

    # First try direct fields
    p1 = match.get("player1_name")
    p2 = match.get("player2_name")

    if p1 and p2:
        return clean_name(p1), clean_name(p2)

    # Then try players object
    players = match.get("players")

    if isinstance(players, dict):

        p1_obj = players.get("p1") or {}
        p2_obj = players.get("p2") or {}

        if isinstance(p1_obj, dict):
            p1 = p1_obj.get("name")

        if isinstance(p2_obj, dict):
            p2 = p2_obj.get("name")

        if p1 and p2:
            return (
                clean_name(p1),
                clean_name(p2)
            )

    return (
        "Player / Team A",
        "Player / Team B"
    )


# =========================================================
# SET SCORE
# =========================================================

def get_set_score(sets):

    if not isinstance(sets, list):
        return 0, 0

    # Official API shape:
    # [1, 0]
    if (
        len(sets) >= 2
        and not isinstance(sets[0], list)
        and not isinstance(sets[1], list)
    ):
        return (
            safe_int(sets[0]),
            safe_int(sets[1])
        )

    # Compatibility with nested shape
    if (
        len(sets) >= 2
        and isinstance(sets[0], list)
        and isinstance(sets[1], list)
    ):
        a = safe_int(sets[0][0]) if sets[0] else 0
        b = safe_int(sets[1][0]) if sets[1] else 0
        return a, b

    return 0, 0


# =========================================================
# GAME SCORE
# =========================================================

def get_games(games):

    if not isinstance(games, list):
        return [], []

    if len(games) < 2:
        return [], []

    p1 = games[0] if isinstance(games[0], list) else []
    p2 = games[1] if isinstance(games[1], list) else []

    p1 = [safe_int(x) for x in p1]
    p2 = [safe_int(x) for x in p2]

    return p1, p2


def format_games(games):

    p1, p2 = get_games(games)

    if not p1 or not p2:
        return "Unavailable"

    pairs = []

    total = max(
        len(p1),
        len(p2)
    )

    for i in range(total):

        a = p1[i] if i < len(p1) else 0
        b = p2[i] if i < len(p2) else 0

        pairs.append(
            f"{a}-{b}"
        )

    return " | ".join(pairs)


# =========================================================
# CURRENT GAME DIFFERENCE
# =========================================================

def current_game_difference(games):

    p1, p2 = get_games(games)

    if not p1 or not p2:
        return 0

    a = p1[-1]
    b = p2[-1]

    return a - b


def total_game_difference(games):

    p1, p2 = get_games(games)

    return (
        sum(p1) - sum(p2)
    )


# =========================================================
# POINT SCORE
# =========================================================

POINT_VALUES = {
    "0": 0,
    "15": 1,
    "30": 2,
    "40": 3,
    "A": 4,
    "AD": 4,
    "ADV": 4,
    "adv": 4,
}


def point_value(point):

    if point is None:
        return 0

    value = str(point).strip()

    return POINT_VALUES.get(
        value,
        0
    )


def get_point_difference(points):

    if not isinstance(points, list):
        return 0

    if len(points) < 2:
        return 0

    return (
        point_value(points[0])
        -
        point_value(points[1])
    )


def format_points(points):

    if not isinstance(points, list):
        return "Unavailable"

    if len(points) < 2:
        return "Unavailable"

    return (
        f"{points[0]} - {points[1]}"
    )


# =========================================================
# START TIME → IST
# =========================================================

def format_ist_time(value):

    if not value:
        return "Start time unavailable"

    try:

        text = str(value).strip()

        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        dt = datetime.fromisoformat(text)

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone.utc
            )

        # IST = UTC + 5:30
        from datetime import timedelta

        ist = dt.astimezone(
            timezone(
                timedelta(hours=5, minutes=30)
            )
        )

        return ist.strftime(
            "%d %b %Y, %I:%M %p IST"
        )

    except Exception:

        return str(value)


# =========================================================
# GET START TIME
# =========================================================

def get_start_time(match):

    value = (
        match.get("start_time")
        or match.get("scheduled_start")
        or match.get("startTime")
    )

    if value:
        return value

    fixture = match.get("fixture")

    if isinstance(fixture, dict):

        return (
            fixture.get("start_time")
            or fixture.get("startTime")
        )

    return None


# =========================================================
# FAVOURITE ESTIMATION
# =========================================================

def estimate_favourite(
    sets,
    games,
    points,
    server
):

    set1, set2 = get_set_score(sets)

    game_diff = total_game_difference(
        games
    )

    current_diff = current_game_difference(
        games
    )

    point_diff = get_point_difference(
        points
    )

    # Main score
    advantage = 0.0

    # Set lead is the strongest signal
    advantage += (
        (set1 - set2) * 1.25
    )

    # Overall game advantage
    advantage += (
        game_diff * 0.08
    )

    # Current set advantage
    advantage += (
        current_diff * 0.12
    )

    # Current point advantage
    advantage += (
        point_diff * 0.12
    )

    # Server has a small live advantage
    if server == 1:
        advantage += 0.08

    elif server == 2:
        advantage -= 0.08

    # Convert to probability
    probability = (
        100.0
        /
        (
            1.0
            +
            math.exp(
                -advantage
            )
        )
    )

    # Avoid fake 100% certainty
    probability = max(
        5,
        min(
            95,
            round(probability)
        )
    )

    p1 = probability
    p2 = 100 - p1

    return p1, p2


# =========================================================
# FAVOURITE REASONS
# =========================================================

def favourite_reasons(
    p1_name,
    p2_name,
    sets,
    games,
    points,
    server,
    p1_probability
):

    set1, set2 = get_set_score(sets)

    game_diff = total_game_difference(
        games
    )

    point_diff = get_point_difference(
        points
    )

    reasons = []

    if set1 > set2:
        reasons.append(
            f"{p1_name} has {set1}-{set2} set lead"
        )

    elif set2 > set1:
        reasons.append(
            f"{p2_name} has {set2}-{set1} set lead"
        )

    if game_diff > 0:
        reasons.append(
            f"{p1_name} has game advantage"
        )

    elif game_diff < 0:
        reasons.append(
            f"{p2_name} has game advantage"
        )

    if point_diff > 0:
        reasons.append(
            f"{p1_name} has current point advantage"
        )

    elif point_diff < 0:
        reasons.append(
            f"{p2_name} has current point advantage"
        )

    if server == 1:
        reasons.append(
            f"{p1_name} is serving"
        )

    elif server == 2:
        reasons.append(
            f"{p2_name} is serving"
        )

    if not reasons:
        reasons.append(
            "Current score is very balanced"
        )

    return reasons[:3]


# =========================================================
# BAR
# =========================================================

def make_bar(percent, width=20):

    filled = round(
        (percent / 100) * width
    )

    filled = max(
        0,
        min(
            width,
            filled
        )
    )

    return (
        "█" * filled
        +
        "░" * (width - filled)
    )


# =========================================================
# FORMAT ONE TENNIS MATCH
# =========================================================

def format_tennis_match(
    match,
    number,
    status="LIVE"
):

    p1_name, p2_name = get_player_names(
        match
    )

    tournament = (
        match.get("tournament")
        or match.get("competition")
        or match.get("event")
        or "Tennis"
    )

    tour = (
        match.get("tour")
        or match.get("category")
        or ""
    )

    score = match.get("score") or {}

    sets = score.get("sets") or []

    games = score.get("games") or []

    points = score.get("points") or []

    server = score.get("server")

    set1, set2 = get_set_score(
        sets
    )

    games_text = format_games(
        games
    )

    points_text = format_points(
        points
    )

    # Server
    if server == 1:
        server_name = p1_name
    elif server == 2:
        server_name = p2_name
    else:
        server_name = "Unknown"

    # Favourite estimate
    p1_probability, p2_probability = (
        estimate_favourite(
            sets,
            games,
            points,
            server
        )
    )

    if p1_probability >= p2_probability:

        favourite = p1_name
        favourite_percent = p1_probability

    else:

        favourite = p2_name
        favourite_percent = p2_probability

    reasons = favourite_reasons(
        p1_name,
        p2_name,
        sets,
        games,
        points,
        server,
        p1_probability
    )

    start_time = get_start_time(
        match
    )

    start_time_text = format_ist_time(
        start_time
    )

    # Header
    if status.upper() == "LIVE":
        header = "🔴 LIVE"
    else:
        header = "🕒 UPCOMING"

    output = []

    output.append(
        f"━━━━━━━━━━━━━━━━━━━━"
    )

    output.append(
        f"🎾 MATCH {number}   {header}"
    )

    output.append(
        f"🏆 {tournament}"
    )

    if tour:
        output.append(
            f"🌍 Tour: {tour}"
        )

    output.append(
        f"⏰ Start: {start_time_text}"
    )

    output.append("")

    output.append(
        f"👥 {p1_name}"
    )

    output.append(
        "VS"
    )

    output.append(
        f"👥 {p2_name}"
    )

    output.append("")

    output.append(
        f"📊 SETS: {set1} - {set2}"
    )

    output.append(
        f"🎯 GAMES: {games_text}"
    )

    output.append(
        f"🎾 POINT: {points_text}"
    )

    if status.upper() == "LIVE":

        output.append(
            f"🏓 Serving: {server_name}"
        )

        output.append("")

        output.append(
            "🔥 PHOENIX LIVE ADVANTAGE"
        )

        output.append(
            f"{p1_name}: {p1_probability}%"
        )

        output.append(
            make_bar(p1_probability)
        )

        output.append(
            f"{p2_name}: {p2_probability}%"
        )

        output.append(
            make_bar(p2_probability)
        )

        output.append("")

        output.append(
            f"⭐ CURRENT FAVOURITE:"
        )

        output.append(
            f"{favourite}"
        )

        output.append(
            f"📈 Estimated Win Chance: "
            f"{favourite_percent}%"
        )

        output.append("")

        output.append(
            "📌 Why?"
        )

        for reason in reasons:
            output.append(
                f"• {reason}"
            )

        output.append("")

        output.append(
            "⚠️ PHOENIX estimate — "
            "not an official bookmaker/API probability."
        )

    return "\n".join(output)


# =========================================================
# LIVE TENNIS
# =========================================================

def get_live_tennis():

    data = tennis_request(
        "/matches?status=live&limit=50"
    )

    if "error" in data:
        return data

    matches = data.get("data", [])

    return matches


# =========================================================
# UPCOMING TENNIS
# =========================================================

def get_upcoming_tennis():

    data = tennis_request(
        "/matches?status=upcoming&limit=50"
    )

    if "error" in data:
        return data

    return data.get(
        "data",
        []
    )


# =========================================================
# TENNIS TEXT RESPONSE
# =========================================================

def tennis_text_response(query):

    live_matches = get_live_tennis()

    if isinstance(live_matches, dict):

        return (
            "🎾 PHOENIX Tennis Error\n\n"
            +
            str(
                live_matches.get(
                    "error",
                    "Unknown error"
                )
            )
        )

    if not live_matches:

        return (
            "🎾 PHOENIX LIVE TENNIS\n\n"
            "ప్రస్తుతం Live tennis matches "
            "కనిపించలేదు."
        )

    output = []

    output.append(
        "🎾 PHOENIX LIVE TENNIS"
    )

    output.append(
        f"🔴 Live Matches: {len(live_matches)}"
    )

    output.append("")

    for index, match in enumerate(
        live_matches,
        start=1
    ):

        try:

            output.append(
                format_tennis_match(
                    match,
                    index,
                    "LIVE"
                )
            )

        except Exception as e:

            print(
                "Match formatting error:",
                str(e)
            )

            output.append(
                f"Match {index}: "
                "Data formatting error"
            )

    return "\n\n".join(output)


# =========================================================
# UPCOMING TENNIS RESPONSE
# =========================================================

def upcoming_tennis_response():

    matches = get_upcoming_tennis()

    if isinstance(matches, dict):

        return (
            "🎾 PHOENIX UPCOMING TENNIS\n\n"
            +
            str(
                matches.get(
                    "error",
                    "Unknown error"
                )
            )
        )

    if not matches:

        return (
            "🎾 Upcoming tennis matches "
            "ప్రస్తుతం కనిపించలేదు."
        )

    output = []

    output.append(
        "🎾 PHOENIX UPCOMING TENNIS"
    )

    output.append(
        f"🕒 Matches: {len(matches)}"
    )

    output.append("")

    for index, match in enumerate(
        matches,
        start=1
    ):

        try:

            output.append(
                format_tennis_match(
                    match,
                    index,
                    "UPCOMING"
                )
            )

        except Exception as e:

            print(
                "Upcoming formatting error:",
                str(e)
            )

    return "\n\n".join(output)


# =========================================================
# HEALTH
# =========================================================

@app.route(
    "/health",
    methods=["GET"]
)
def health():

    return jsonify({
        "status": "ok",
        "service": "PHOENIX AI",
        "gemini": bool(
            GEMINI_API_KEY
        ),
        "tennis": bool(
            TENNIS_API_KEY
        ),
        "web_search": ENABLE_WEB_SEARCH
    })


# =========================================================
# LIVE TENNIS JSON API
# =========================================================

@app.route(
    "/tennis/live",
    methods=["GET"]
)
def tennis_live_api():

    matches = get_live_tennis()

    if isinstance(matches, dict):

        return jsonify(
            matches
        ), 500

    return jsonify({
        "status": "success",
        "count": len(matches),
        "data": matches
    })


# =========================================================
# UPCOMING TENNIS JSON API
# =========================================================

@app.route(
    "/tennis/upcoming",
    methods=["GET"]
)
def tennis_upcoming_api():

    matches = get_upcoming_tennis()

    if isinstance(matches, dict):

        return jsonify(
            matches
        ), 500

    return jsonify({
        "status": "success",
        "count": len(matches),
        "data": matches
    })


# =========================================================
# MAIN /run
# =========================================================

@app.route(
    "/run",
    methods=["GET", "POST"]
)
def run_query():

    query = ""

    # GET
    if request.method == "GET":

        query = request.args.get(
            "query",
            ""
        )

    # POST
    elif request.method == "POST":

        if request.is_json:

            body = request.get_json(
                silent=True
            ) or {}

            query = body.get(
                "query",
                ""
            )

        else:

            query = request.form.get(
                "query",
                ""
            )

    query = str(
        query
    ).strip()

    if not query:

        return jsonify({
            "status": "error",
            "data": "Query parameter missing."
        }), 400

    print(
        "PHOENIX QUERY:",
        query
    )

    # -----------------------------------------------------
    # TENNIS
    # -----------------------------------------------------

    if is_tennis_query(query):

        answer = tennis_text_response(
            query
        )

        return jsonify({
            "status": "success",
            "title": "🎾 PHOENIX LIVE TENNIS",
            "data": answer
        })


    # -----------------------------------------------------
    # WEB / CURRENT INFORMATION
    # -----------------------------------------------------

    web_needed = is_web_query(
        query
    )

    answer = ask_gemini(
        query,
        use_web=web_needed
    )

    return jsonify({
        "status": "success",
        "title": "🦅 PHOENIX AI",
        "data": answer
    })


# =========================================================
# HOME
# =========================================================

@app.route(
    "/",
    methods=["GET"]
)
def home():

    return (
        "🦅 PHOENIX AI Backend is Online\n"
        "AI: Ready\n"
        "Tennis: Ready\n"
        "Live Web Search: Ready"
    )


# =========================================================
# RUN LOCAL
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
