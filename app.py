@app.route('/run', methods=['GET', 'POST'])
def run_query():
    # URL parameter (?query=) నుండి డేటా తీసుకుంటుంది
    query = request.args.get('query', '')
    
    # ఒకవేళ ఫ్రంటెండ్ నుండి POST రిక్వెస్ట్ వస్తే JSON నుండి తీసుకుంటుంది
    if not query and request.is_json:
        query = request.json.get('query', '')
        
    if not query:
        return "Error: Query text missing", 400
        
    reply = ask_gemini(query)
    return reply  # నేరుగా టెక్స్ట్ రెస్పాన్స్ పంపుతుంది (ఫ్రంటెండ్ లో ఈజీగా డిస్ప్లే అవుతుంది)
