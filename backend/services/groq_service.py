import os
from groq import Groq
from typing import List, Dict

_client = None

def get_groq_client():
    """Lazy Groq client — re-reads GROQ_API_KEY on every call until a valid key is found.
    This prevents the startup-caching bug where Railway injects env vars after module load.
    """
    global _client
    # Always re-check env; if key wasn't set at startup it may be available now
    api_key = os.environ.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
    if not api_key:
        print("[ERROR] GROQ_API_KEY is not set in environment")
        return None
    # Rebuild client only if we don't have one yet (or key changed)
    if _client is None:
        _client = Groq(api_key=api_key)
        print(f"[OK] Groq client initialized with key prefix={api_key[:8]}...")
    return _client

def _get_model() -> str:
    """Get model name from env var, with a safe default."""
    return os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

def chat_with_context(messages: List[Dict]) -> str:
    """Chat with context for RAG. messages should be a list of {role, content} dicts."""
    client = get_groq_client()
    if not client:
        return "Error: GROQ_API_KEY not configured"
    try:
        response = client.chat.completions.create(
            model=_get_model(),
            messages=messages,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

def predict_questions(subject: str, unit: str = None, num_questions: int = 5) -> Dict:
    """Predict possible questions for a subject"""
    client = get_groq_client()
    if not client:
        return {"error": "GROQ_API_KEY not configured"}
    
    prompt = f"""Generate {num_questions} important questions for {subject}"""
    if unit:
        prompt += f" - Unit {unit}"
    prompt += """. Return as JSON array with 'question' and 'difficulty' fields."""
    
    try:
        response = client.chat.completions.create(
            model=_get_model(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return {"questions": response.choices[0].message.content, "subject": subject, "unit": unit}
    except Exception as e:
        return {"error": str(e)}

def chat_with_subject(query: str, subject: str, context: str) -> str:
    """Chat specific to a subject with context"""
    client = get_groq_client()
    if not client:
        return "Error: GROQ_API_KEY not configured"
    
    messages = [
        {"role": "system", "content": f"You are a VTU {subject} expert. Answer based on context."},
        {"role": "user", "content": f"Context: {context}\n\nQuestion: {query}"}
    ]
    
    try:
        response = client.chat.completions.create(
            model=_get_model(),
            messages=messages,
            temperature=0.5
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"