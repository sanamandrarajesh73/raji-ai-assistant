    # నీ existing if/elif కండిషన్ల కింద చివరన ఇలా ఉంచు:
    else:
        return jsonify({
            "status": "success",
            "title": "🤖 JARVIS",
            "data": f"నమస్తే! మీరు అడిగింది: '{query}'. ప్రస్తుతానికి క్రికెట్, టెన్నిస్ లేదా స్టాక్స్ సమాచారం అందుబాటులో ఉంది."
        })
