import os
import requests

api_key = os.environ.get("GROQ_API_KEY", "").strip()
if not api_key:
    print("❌ GROQ_API_KEY కనిపించడం లేదు!")
else:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    # 1. API Key చెక్ చేయడానికి Models లిస్ట్ అడగడం
    r = requests.get("https://api.groq.com/openai/v1/models", headers=headers, timeout=15)
    print("Models Status:", r.status_code)
    if r.status_code == 200:
        models = [m["id"] for m in r.json().get("data", [])]
        print("✅ API Key పర్ఫెక్ట్‌గా పనిచేస్తోంది! అందుబాటులో ఉన్న కొన్ని మోడల్స్:", models[:5])
    else:
        print("❌ API Key / Request లోపం:", r.text)
                  
