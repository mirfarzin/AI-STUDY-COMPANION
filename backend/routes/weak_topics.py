from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, model_validator
from typing import List, Any
import json

from services.groq_service import chat_with_context

router = APIRouter()


class IncorrectQuestion(BaseModel):
    question: str
    user_answer: str = ""
    correct_answer: str = ""

    @model_validator(mode="before")
    @classmethod
    def handle_frontend_fields(cls, data: Any) -> Any:
        """Accept 'selected' and 'correct' field names sent by QuizPane.jsx."""
        if isinstance(data, dict):
            if "selected" in data and "user_answer" not in data:
                data["user_answer"] = data["selected"]
            if "correct" in data and "correct_answer" not in data:
                data["correct_answer"] = data["correct"]
        return data


class WeakTopicsRequest(BaseModel):
    subject: str
    incorrect_questions: List[IncorrectQuestion]


@router.post("/weak-topics")
async def analyze_weaknesses(req: WeakTopicsRequest):
    if not req.incorrect_questions:
        return []

    questions_context = ""
    for i, q in enumerate(req.incorrect_questions):
        questions_context += (
            f"Q{i+1}: {q.question}\n"
            f"User selected: {q.user_answer}\n"
            f"Correct answer: {q.correct_answer}\n\n"
        )

    sys_prompt = (
        "You are an AI study coach analyzing a student's quiz performance. "
        "The user got several questions wrong. Group the missed questions into high-level conceptual 'topics'. "
        "Return the analysis as a JSON array where each object has:\n"
        "- 'topic' (string: name of the weak conceptual area)\n"
        "- 'suggestion' (string: actionable study tip)\n"
        "- 'question_count' (int: number of questions missed in this area)\n"
        "Return valid JSON ONLY, no markdown blocks, no extra text."
    )

    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": f"Subject: {req.subject}\n\nMissed Questions:\n{questions_context}"},
    ]

    try:
        response_text = chat_with_context(messages)
    except Exception as e:
        print(f"[ERROR] Groq call failed in weak-topics: {e}")
        raise HTTPException(status_code=502, detail="AI service temporarily unavailable.")

    if not response_text or response_text.startswith("Error:"):
        raise HTTPException(status_code=502, detail=f"AI service error: {response_text}")

    try:
        cleaned = response_text.replace("```json", "").replace("```", "").strip()
        analysis = json.loads(cleaned)
        if not isinstance(analysis, list):
            raise ValueError("LLM did not return a JSON list")
        return analysis
    except Exception as e:
        print(f"Error parsing weak topics JSON: {e}\nRaw: {response_text}")
        raise HTTPException(status_code=400, detail="Invalid JSON from LLM")
