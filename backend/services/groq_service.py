import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("WARNING: GROQ_API_KEY not set. Chat will not work.")
    _client = None
else:
    _client = Groq(api_key=api_key)

_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")


def chat_with_context(query: str, context_chunks: list[str]) -> str:
    if _client is None:
        return {"error": "GROQ_API_KEY not configured"}
    
    context = "\n\n---\n\n".join(context_chunks)
    prompt = f"""You are a helpful VTU study assistant. Answer the student's question using ONLY the provided notes.

NOTES:
{context}

QUESTION: {query}

Give a clear, well-structured answer. Use bullet points or numbered lists where appropriate. If the answer isn't in the notes, say so clearly."""

    response = _client.chat.completions.create(
        model=_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1024,
    )
    return response.choices[0].message.content


def predict_questions(chunks: list[str]) -> str:
    if _client is None:
        return {"error": "GROQ_API_KEY not configured"}
    
    context = "\n\n".join(chunks[:15])
    prompt = f"""You are a VTU exam expert. Based on the study notes below, generate exactly 10 important questions likely to appear in VTU exams.

NOTES:
{context}

Format your response EXACTLY like this for each question:
Q1. [Question here]
A: [Brief but complete answer here]

Q2. [Question here]
A: [Brief but complete answer here]

(continue for all 10 questions)

Focus on conceptual understanding, definitions, comparisons, and application-based questions typical of VTU pattern."""

    response = _client.chat.completions.create(
        model=_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
        max_tokens=2048,
    )
    return response.choices[0].message.content
