from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import json

from services.groq_service import chat_with_context

router = APIRouter()

class IncorrectQuestion(BaseModel):
    question: str
    user_answer: str
    correct_answer: str

class WeakTopicsRequest(BaseModel):
    subject: str
    incorrect_questions: List[IncorrectQuestion]

@router.post("/api/weak-topics")
async def analyze_weaknesses(req: WeakTopicsRequest):
    if not req.incorrect_questions:
        return []
        
    questions_context = ""
    for i, q in enumerate(req.incorrect_questions):
        questions_context += f"Q{i+1}: {q.question}\nUser selected: {q.user_answer}\nCorrect: {q.correct_answer}\n\n"
        
    sys_prompt = (
        "You are an AI study coach analyzing a student's quiz performance. "
        "The user got several questions wrong. Group the missed questions into high-level conceptual 'topics'. "
        "Return the analysis as a JSON array where each object has:\n"
        "- 'topic' (string: name of the weak conceptual area)\n"
        "- 'suggestion' (string: actionable study tip)\n"
        "- 'question_count' (int: number of questions missed in this area)\n"
        "Return valid JSON ONLY, no markdown blocks."
    )
    
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": f"Subject: {req.subject}\n\nMissed Questions:\n{questions_context}"}
    ]
    
    response_text = chat_with_context(messages)
    
    try:
        cleaned = response_text.replace("```json", "").replace("```", "").strip()
        analysis = json.loads(cleaned)
        return analysis
    except Exception as e:
        print(f"Error parsing weak topics JSON: {e}\nRaw output: {response_text}")
        raise HTTPException(status_code=500, detail="Failed to analyze weak topics.")
