import os
from groq import Groq

_client = None

def get_groq_client():
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            _client = Groq(api_key=api_key)
            print("✅ Groq client initialized")
        else:
            print("⚠️ GROQ_API_KEY not set - chat disabled")
    return _client

def chat_with_context(messages):
    client = get_groq_client()
    if not client:
        return {"error": "GROQ_API_KEY not configured"}
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=messages
        )
        return response.choices[0].message.content
    except Exception as e:
        return {"error": str(e)}
