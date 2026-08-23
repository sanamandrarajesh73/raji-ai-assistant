from flask import Flask, request, Response, jsonify
import requests
import os
from datetime import date

app = Flask(__name__)

# ============================================================
# API KEYS
# ============================================================
CRICKET_API_KEY = "5393947d-ab90-478e-ab15-6e9eb83989c1"
GROQ_API_KEY = "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"

# ============================================================
# PHOENIX DATA WALLET
# ============================================================
wallet = {
    "daily_limit_gb": 2.0,
    "used_gb": 0.0,
    "days_remaining": 30,
    "last_update": str(date.today())
}

def get_wallet_data():
    daily = max(0.0, float(wallet["daily_limit_gb"]))
    used = max(0.0, float(wallet["used_gb"]))
    days = max(0, int(wallet["days_remaining"]))

    used = min(used, daily)
    unused = max(0.0, daily - used)
    potential_credit = unused * days
    usage_percent = round((used / daily) * 100, 2) if daily > 0 else 0

    return {
        "daily_data_balance_gb": round(daily, 2),
        "used_data_gb": round(used, 2),
        "unused_data_gb": round(unused, 2),
        "days_remaining": days,
        "potential_data_credit_gb": round(potential_credit, 2),
        "usage_percent": usage_percent,
        "last_update": wallet["last_update"]
    }

# ============================================================
# API ENDPOINTS
# ============================================================

@app.route("/", methods=["GET"])
def home():
    return jsonify({"app": "Phoenix Data Wallet + Jarvis AI", "version": "1.0", "status": "online"})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "Phoenix Engine Active"})

@app.route("/wallet", methods=["GET"])
def get_wallet():
    return jsonify({"success": True, "wallet": get_wallet_data()})

@app.route("/wallet/update", methods=["POST"])
def update_wallet():
    try:
        data = request.get_json(silent=True) or {}
        if "daily_data_gb" in data:
            wallet["daily_limit_gb"] = float(data["daily_data_gb"])
        if "used_data_gb" in data:
            wallet["used_gb"] = float(data["used_data_gb"])
        if "days_remaining" in data:
            wallet["days_remaining"] = int(data["days_remaining"])
        wallet["last_update"] = str(date.today())
        return jsonify({"success": True, "message": "Wallet Updated Successfully", "wallet": get_wallet_data()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/wallet/expiry", methods=["GET"])
def expiry_watch():
    data = get_wallet_data()
    unused, days = data["unused_data_gb"], data["days_remaining"]
    if unused <= 0:
        msg, level = "ఈరోజు unused data లేదు.", "safe"
    elif days <= 1:
        msg, level = f"⚠️ సుమారు {unused:.2f} GB unused data expiryకి దగ్గరలో ఉంది.", "warning"
    else:
        msg, level = f"సుమారు {unused:.2f} GB unused data ఉంది. Planలో {days} రోజులు ఉన్నాయి.", "normal"
    return jsonify({"success": True, "expiry_watch": {"level": level, "message": msg, "unused_gb": unused, "days": days}})

@app.route("/wallet/credit", methods=["GET"])
def data_credit():
    data = get_wallet_data()
    return jsonify({
        "success": True,
        "data_credit": {
            "potential_credit_gb": data["potential_data_credit_gb"],
            "type": "SIMULATION",
            "message": "Phoenix prototype data credit simulation active."
        }
    })

@app.route("/wallet/insight", methods=["GET"])
def phoenix_insight():
    data = get_wallet_data()
    daily, used, unused = data["daily_data_balance_gb"], data["used_data_gb"], data["unused_data_gb"]
    if daily <= 0:
        insight = "ముందుగా daily data allowance set చేయాలి."
    elif used == 0:
        insight = f"ఈరోజు usage 0 GB. సుమారు {daily:.2f} GB unusedగా ఉంది."
    elif unused >= daily * 0.5:
        insight = f"నీ allowanceలో {unused:.2f} GB ఇంకా మిగిలింది."
    else:
        insight = "ఈరోజు allowance పూర్తి కావచ్చింది."
    return jsonify({"success": True, "phoenix_insight": insight})

@app.route("/wallet/reset", methods=["POST"])
def reset_day():
    wallet["used_gb"] = 0.0
    if wallet["days_remaining"] > 0:
        wallet["days_remaining"] -= 1
    wallet["last_update"] = str(date.today())
    return jsonify({"success": True, "message": "Phoenix daily wallet reset completed.", "wallet": get_wallet_data()})

# ============================================================
# CHAT ENDPOINT (JARVIS AI + CRICKET + WALLET)
# ============================================================

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(silent=True) or {}
        user_message = str(data.get("message", "")).strip()
        if not user_message:
            user_message = request.form.get("message", "") or request.data.decode("utf-8", errors="ignore")

        user_message_clean = user_message.lower().strip()

        # 1. PHOENIX DATA WALLET
        if "data wallet" in user_message_clean or "డేటా వాలెట్" in user_message_clean:
            w = get_wallet_data()
            reply = (
                "🔥 PHOENIX DATA WALLET 🔥\n"
                "══════════════════════\n\n"
                f"📊 Daily Data Balance: {w['daily_data_balance_gb']:.2f} GB\n"
                f"📉 Used Data: {w['used_data_gb']:.2f} GB\n"
                f"💾 Unused Data: {w['unused_data_gb']:.2f} GB\n"
                f"⏳ Days Remaining: {w['days_remaining']}\n"
                f"🪙 Data Credit Simulation: {w['potential_data_credit_gb']:.2f} GB\n"
                f"🧠 Usage: {w['usage_percent']:.2f}%\n"
            )
            return Response(reply, mimetype="text/plain; charset=utf-8")

        # 2. CRICKET
        elif "cricket" in user_message_clean or "క్రికెట్" in user_message_clean:
            url = f"https://api.cricapi.com/v1/currentMatches?apikey={CRICKET_API_KEY}&offset=0"
            res = requests.get(url, timeout=15).json().get("data", [])
            live_matches = [m for m in res if not m.get("matchEnded", False)]
            if live_matches:
                reply = "🏏 రాజేష్ AI - మ్యాచ్ ప్రిడిక్షన్స్ 🏏\n═════════════════════════\n\n"
                for match in live_matches:
                    name = match.get("name", "Match")
                    teams = match.get("teams", [])
                    fav = teams[0] if len(teams) > 0 else "Team A"
                    reply += f"🏆 {name}\n⭐️ గెలిచే టీమ్: 👉 {fav}\n\n"
                return Response(reply.strip(), mimetype="text/plain; charset=utf-8")
            return Response("ప్రస్తుతం ఎటువంటి లైవ్ మ్యాచ్‌లు లేవు నేస్తమా.", mimetype="text/plain; charset=utf-8")

        # 3. GREETINGS
        elif user_message_clean in ["hello", "hallo", "హాయ్", "hi"]:
            return Response("హలో నేస్తమా! నేను నీ పర్సనల్ Phoenix + Jarvis AI ని. నీకు ఏ ప్రశ్న ఉన్నా అడుగు, సమాధానం ఇస్తాను.", mimetype="text/plain; charset=utf-8")

        # 4. UNIVERSAL GROQ AI (JARVIS - ఏ ప్రశ్నకైనా సమాధానం ఇస్తుంది)
        else:
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {
                        "role": "system",
                        "content": "నువ్వు 'జార్విస్' అనే అత్యంత తెలివైన ఆల్ రౌండర్ AI అసిస్టెంట్. యూజర్ అడిగే ఏ విషయానికైనా (మెడికల్, డిప్లొమా, సైన్స్, కాథ్ ల్యాబ్, కోడింగ్, జనరల్ నాలెడ్జ్) చాలా వివరంగా, స్పష్టంగా తెలుగులో సమాధానం ఇవ్వు."
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ]
            }
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=30)
            res_data = res.json()
            
            if "choices" in res_data and len(res_data["choices"]) > 0:
                answer = res_data["choices"][0]["message"]["content"]
                return Response(answer, mimetype="text/plain; charset=utf-8")
            else:
                return Response(f"AI Error: {res.text}", mimetype="text/plain; charset=utf-8")

    except Exception as e:
        return Response(f"Error Details: {str(e)}", mimetype="text/plain; charset=utf-8")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
