
import os
import json
import math
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone, timedelta

from flask import Flask, request, jsonify
from flask_cors import CORS

# =====================================================
# PHOENIX TENNIS LIVE - STANDALONE BACKEND
# =====================================================

app = Flask(__name__)
CORS(app)

API_KEY = os.getenv("TENNIS_API_KEY", "").strip()
BASE_URL = "https://api.livetennisapi.com/api/public/v1"
IST = timezone(timedelta(hours=5, minutes=30))

# Keep requests low: free plan has daily and per-minute limits.
CACHE = {}
CACHE_SECONDS = 15


# =====================================================
# COMMON HELPERS
# =====================================================

def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_json(url):
    if not API_KEY:
        raise RuntimeError(
            "TENNIS_API_KEY is missing in Render Environment Variables."
        )

    req = urllib.request.Request(
        url,
        headers={
            "X-API-Key": API_KEY,
            "Accept": "application/json",
            "User-Agent": "PHOENIX-TENNIS/1.0"
        },
        method="GET"
    )

    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def api_get(endpoint, params=None):
    params = params or {}
    query_string = urllib.parse.urlencode(params)
    url = BASE_URL + endpoint

    if query_string:
        url += "?" + query_string

    # Short cache reduces repeated API calls.
    now = time.time()
    cached = CACHE.get(url)

    if cached and now - cached["time"] < CACHE_SECONDS:
        return cached["data"]

    data = get_json(url)
    CACHE[url] = {"time": now, "data": data}
    return data


def list_matches(status):
    result = api_get(
        "/matches",
        {"status": status, "limit": 50}
    )

    if isinstance(result, list):
        return result

    if isinstance(result, dict):
        rows = result.get("data", [])
        return rows if isinstance(rows, list) else []

    return []


def first_value(*values, default=None):
    for value in values:
        if value is not None and value != "":
            return value
    return default


# =====================================================
# PLAYER NAMES / COUNTRY FLAGS
# =====================================================

COUNTRY_FLAGS = {
    "india": "🇮🇳",
    "ind": "🇮🇳",
    "united kingdom": "🇬🇧",
    "great britain": "🇬🇧",
    "gb": "🇬🇧",
    "gbr": "🇬🇧",
    "england": "🏴",
    "united states": "🇺🇸",
    "usa": "🇺🇸",
    "us": "🇺🇸",
    "australia": "🇦🇺",
    "aus": "🇦🇺",
    "new zealand": "🇳🇿",
    "nz": "🇳🇿",
    "nzl": "🇳🇿",
    "france": "🇫🇷",
    "fra": "🇫🇷",
    "italy": "🇮🇹",
    "ita": "🇮🇹",
    "spain": "🇪🇸",
    "esp": "🇪🇸",
    "germany": "🇩🇪",
    "ger": "🇩🇪",
    "japan": "🇯🇵",
    "jpn": "🇯🇵",
    "poland": "🇵🇱",
    "pol": "🇵🇱",
    "romania": "🇷🇴",
    "rou": "🇷🇴",
    "canada": "🇨🇦",
    "can": "🇨🇦",
    "brazil": "🇧🇷",
    "bra": "🇧🇷",
    "china": "🇨🇳",
    "chn": "🇨🇳",
    "argentina": "🇦🇷",
    "arg": "🇦🇷",
    "serbia": "🇷🇸",
    "srb": "🇷🇸",
    "ukraine": "🇺🇦",
    "ukr": "🇺🇦",
    "czech republic": "🇨🇿",
    "czechia": "🇨🇿",
    "cze": "🇨🇿",
    "switzerland": "🇨🇭",
    "sui": "🇨🇭",
    "netherlands": "🇳🇱",
    "ned": "🇳🇱",
    "belgium": "🇧🇪",
    "bel": "🇧🇪",
    "croatia": "🇭🇷",
    "cro": "🇭🇷",
    "greece": "🇬🇷",
    "gre": "🇬🇷",
    "south korea": "🇰🇷",
    "kor": "🇰🇷",
    "south africa": "🇿🇦",
    "rsa": "🇿🇦",
    "portugal": "🇵🇹",
    "por": "🇵🇹",
    "sweden": "🇸🇪",
    "swe": "🇸🇪",
    "denmark": "🇩🇰",
    "den": "🇩🇰",
    "bulgaria": "🇧🇬",
    "bul": "🇧🇬",
    "turkey": "🇹🇷",
    "tur": "🇹🇷",
    "mexico": "🇲🇽",
    "mex": "🇲🇽",
}


def country_flag(person):
    if not isinstance(person, dict):
        return "🎾"

    country = first_value(
        person.get("country"),
        person.get("country_name"),
        person.get("country_code"),
        person.get("nationality"),
        default=""
    )

    key = str(country).strip().lower()
    return COUNTRY_FLAGS.get(key, "🎾")


def get_players(match):
    players = match.get("players") or {}

    p1_obj = players.get("p1") or {}
    p2_obj = players.get("p2") or {}

    if not isinstance(p1_obj, dict):
        p1_obj = {}
    if not isinstance(p2_obj, dict):
        p2_obj = {}

    p1_name = first_value(
        match.get("player1_name"),
        p1_obj.get("name"),
        default="Player / Team A"
    )

    p2_name = first_value(
        match.get("player2_name"),
        p2_obj.get("name"),
        default="Player / Team B"
    )

    return (
        str(p1_name),
        str(p2_name),
        country_flag(p1_obj),
        country_flag(p2_obj)
    )


# =====================================================
# TIME AND COUNTDOWN
# =====================================================

def parse_datetime(value):
    if not value:
        return None

    try:
        text = str(value).strip()

        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        dt = datetime.fromisoformat(text)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(IST)

    except (ValueError, TypeError):
        return None


def get_start_value(match):
    score = match.get("score") or {}
    fixture = match.get("fixture") or {}

    return first_value(
        match.get("scheduled_time"),
        match.get("start_time"),
        match.get("scheduled_start"),
        match.get("startTime"),
        fixture.get("scheduled_time"),
        fixture.get("start_time"),
        fixture.get("startTime"),
        score.get("scheduled_time")
    )


def time_details(match, is_live=False):
    scheduled = parse_datetime(get_start_value(match))

    score = match.get("score") or {}
    live_at = parse_datetime(
        first_value(
            match.get("live_at"),
            score.get("live_at")
        )
    )

    if scheduled:
        start_text = scheduled.strftime(
            "%d %b %Y, %I:%M %p IST"
        )
    else:
        start_text = "Start time unavailable"

    countdown = ""

    if not is_live and scheduled:
        seconds = int(
            (scheduled - datetime.now(IST)).total_seconds()
        )

        if seconds > 0:
            days, remainder = divmod(seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, secs = divmod(remainder, 60)

            if days:
                countdown = (
                    f"{days}d {hours:02}h {minutes:02}m"
                )
            else:
                countdown = (
                    f"{hours:02}h {minutes:02}m {secs:02}s"
                )
        else:
            countdown = (
                "Scheduled time passed; waiting for live update"
            )

    if is_live and live_at:
        live_text = live_at.strftime(
            "%d %b %Y, %I:%M %p IST"
        )
    elif is_live:
        live_text = (
            "Unavailable (API has no live-start timestamp)"
        )
    else:
        live_text = ""

    return start_text, countdown, live_text


# =====================================================
# SCORE FORMATTERS
# =====================================================

def get_score(match):
    score = match.get("score")

    if not isinstance(score, dict):
        score = {}

    # Some API responses may place score fields at top level.
    sets = first_value(
        score.get("sets"),
        match.get("sets"),
        default=[]
    )
    games = first_value(
        score.get("games"),
        match.get("games"),
        default=[]
    )
    points = first_value(
        score.get("points"),
        match.get("points"),
        default=[]
    )
    server = first_value(
        score.get("server"),
        match.get("server")
    )

    return sets, games, points, server


def format_sets(sets):
    if not isinstance(sets, list) or len(sets) < 2:
        return "Unavailable"

    # API: [sets_player1, sets_player2]
    if not isinstance(sets[0], list):
        return f"{sets[0]} - {sets[1]}"

    # Compatibility with nested shapes
    try:
        return f"{sets[0][0]} - {sets[1][0]}"
    except (IndexError, TypeError):
        return "Unavailable"


def format_games(games):
    if not isinstance(games, list) or len(games) < 2:
        return "Unavailable"

    p1 = games[0] if isinstance(games[0], list) else []
    p2 = games[1] if isinstance(games[1], list) else []

    if not p1 or not p2:
        return "Unavailable"

    pairs = []

    for i in range(max(len(p1), len(p2))):
        a = p1[i] if i < len(p1) else "-"
        b = p2[i] if i < len(p2) else "-"
        pairs.append(f"{a}-{b}")

    return " | ".join(pairs)


def format_points(points):
    if not isinstance(points, list) or len(points) < 2:
        return "Unavailable"

    return f"{points[0]} - {points[1]}"


def server_name(server, p1_name, p2_name):
    if str(server) == "1":
        return p1_name
    if str(server) == "2":
        return p2_name
    return "Unavailable"


# =====================================================
# HONEST LIVE ADVANTAGE ESTIMATE
# =====================================================

POINT_VALUES = {
    "0": 0,
    "15": 1,
    "30": 2,
    "40": 3,
    "A": 4,
    "AD": 4,
    "ADV": 4
}


def estimate_chance(sets, games, points, server):
    # This is a simple heuristic, not a trained match model.
    set1 = set2 = 0

    if isinstance(sets, list) and len(sets) >= 2:
        if not isinstance(sets[0], list):
            set1 = safe_int(sets[0])
            set2 = safe_int(sets[1])

    game_diff = 0

    if isinstance(games, list) and len(games) >= 2:
        g1 = games[0] if isinstance(games[0], list) else []
        g2 = games[1] if isinstance(games[1], list) else []

        game_diff = sum(safe_int(x) for x in g1) - sum(
            safe_int(x) for x in g2
        )

    point_diff = 0

    if isinstance(points, list) and len(points) >= 2:
        point_diff = (
            POINT_VALUES.get(str(points[0]).upper(), 0)
            - POINT_VALUES.get(str(points[1]).upper(), 0)
        )

    advantage = (
        (set1 - set2) * 1.25
        + game_diff * 0.08
        + point_diff * 0.12
    )

    if str(server) == "1":
        advantage += 0.08
    elif str(server) == "2":
        advantage -= 0.08

    try:
        p1 = 100 / (1 + math.exp(-advantage))
    except OverflowError:
        p1 = 95 if advantage > 0 else 5

    p1 = max(5, min(95, round(p1)))
    return p1, 100 - p1


# =====================================================
# ONE MATCH CARD
# =====================================================

def format_match(match, index, is_live):
    p1, p2, flag1, flag2 = get_players(match)

    tournament = first_value(
        match.get("tournament"),
        match.get("competition"),
        match.get("event"),
        default="Tennis"
    )

    tour = first_value(
        match.get("tour"),
        match.get("category"),
        default=""
    )

    match_id = first_value(
        match.get("id"),
        match.get("match_id"),
        default="Unavailable"
    )

    sets, games, points, server = get_score(match)
    start_text, countdown, live_text = time_details(
        match, is_live
    )

    output = [
        "━━━━━━━━━━━━━━━━━━━━",
        f"🎾 MATCH {index}  {'🔴 LIVE' if is_live else '🕒 UPCOMING'}",
        f"🏆 {tournament}",
    ]

    if tour:
        output.append(f"🌍 Tour: {tour}")

    output.extend([
        f"🆔 Match ID: {match_id}",
        f"⏰ Start: {start_text}"
    ])

    if is_live:
        output.append(f"🔴 Live Since: {live_text}")
    elif countdown:
        output.append(f"⏳ Countdown: {countdown}")

    output.extend([
        "",
        f"{flag1} {p1}",
        "             VS",
        f"{flag2} {p2}",
        ""
    ])

    # Upcoming matches may not have a score yet.
    if not is_live and not games and not sets:
        output.append("📊 Score: Match not started / score unavailable")
        return "\n".join(output)

    output.extend([
        f"📊 SETS: {format_sets(sets)}",
        f"🎯 GAMES: {format_games(games)}",
        f"🎾 POINTS: {format_points(points)}"
    ])

    if is_live:
        serving = server_name(server, p1, p2)
        p1_chance, p2_chance = estimate_chance(
            sets, games, points, server
        )

        output.extend([
            f"🏓 Serving: {serving}",
            "",
            "🔥 PHOENIX LIVE ADVANTAGE (ESTIMATE)",
            f"{flag1} {p1}: {p1_chance}%",
            f"{flag2} {p2}: {p2_chance}%",
            ""
        ])

        if p1_chance > p2_chance:
            output.append(f"⭐ Current estimate favourite: {p1}")
        elif p2_chance > p1_chance:
            output.append(f"⭐ Current estimate favourite: {p2}")
        else:
            output.append("⭐ Current estimate: Even")

        output.append(
            "⚠️ Estimate only; not an official win probability."
        )

    return "\n".join(output)


# =====================================================
# BUILD LIVE / UPCOMING TEXT
# =====================================================

def build_matches(status):
    is_live = status == "live"
    matches = list_matches(status)

    if not matches:
        if is_live:
            return (
                "🎾 PHOENIX TENNIS LIVE\n\n"
                "ప్రస్తుతం APIలో లైవ్ మ్యాచ్‌లు కనిపించడం లేదు.\n"
                "ఇది API సమస్య అని తప్పనిసరిగా అర్థం కాదు."
            ), 0

        return (
            "🎾 PHOENIX UPCOMING TENNIS\n\n"
            "ప్రస్తుతం రాబోయే మ్యాచ్‌లు APIలో కనిపించడం లేదు."
        ), 0

    cards = []

    for index, match in enumerate(matches, start=1):
        if isinstance(match, dict):
            cards.append(
                format_match(match, index, is_live)
            )

    title = (
        "🎾 PHOENIX TENNIS LIVE"
        if is_live
        else "🎾 PHOENIX UPCOMING TENNIS"
    )

    return title + "\n\n" + "\n\n".join(cards), len(cards)


# =====================================================
# FLASK ROUTES
# =====================================================

@app.get("/")
def home():
    return jsonify({
        "app": "PHOENIX TENNIS LIVE",
        "status": "running",
        "endpoints": [
            "/health",
            "/tennis/live",
            "/tennis/upcoming",
            "/run?query=tennis%20live"
        ]
    })


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "PHOENIX TENNIS LIVE",
        "api_key_configured": bool(API_KEY),
        "timezone": "Asia/Kolkata"
    })


@app.get("/tennis/live")
def tennis_live():
    try:
        text, count = build_matches("live")
        return jsonify({
            "ok": True,
            "type": "live",
            "count": count,
            "data": text
        })
    except urllib.error.HTTPError as e:
        if e.code == 429:
            message = "API rate limit reached. Please wait before retrying."
        elif e.code == 401:
            message = "Tennis API key was rejected. Check Render Environment Variables."
        elif e.code == 403:
            message = "Tennis API plan does not allow this request."
        else:
            message = f"Tennis API HTTP error: {e.code}"

        return jsonify({
            "ok": False,
            "data": message
        }), 502
    except Exception as e:
        app.logger.exception("Live tennis failed")
        return jsonify({
            "ok": False,
            "data": "Live tennis data could not be loaded. Check API key and service status."
        }), 502


@app.get("/tennis/upcoming")
def tennis_upcoming():
    try:
        text, count = build_matches("upcoming")
        return jsonify({
            "ok": True,
            "type": "upcoming",
            "count": count,
            "data": text
        })
    except urllib.error.HTTPError as e:
        return jsonify({
            "ok": False,
            "data": f"Tennis API HTTP error: {e.code}"
        }), 502
    except Exception:
        app.logger.exception("Upcoming tennis failed")
        return jsonify({
            "ok": False,
            "data": "Upcoming tennis data could not be loaded. Check API key and service status."
        }), 502


@app.get("/run")
def run():
    query = request.args.get("query", "").strip().lower()

    if any(word in query for word in [
        "upcoming", "schedule", "fixture", "రాబోయే", "షెడ్యూల్"
    ]):
        return tennis_upcoming()

    if any(word in query for word in [
        "tennis", "live", "score", "టెన్నిస్", "లైవ్", "స్కోర్"
    ]):
        return tennis_live()

    return jsonify({
        "ok": True,
        "data": (
            "PHOENIX TENNIS LIVE\n"
            "లైవ్ మ్యాచ్‌ల కోసం 'tennis live' అని అడగండి.\n"
            "రాబోయే మ్యాచ్‌ల కోసం 'tennis upcoming' అని అడగండి."
        )
    })


# =====================================================
# START
# =====================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=False
)
    
