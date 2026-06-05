from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import json

from services.qdrant_service import query_chunks
from services.groq_service import chat_with_context

router = APIRouter()

class QuizResponse(BaseModel):
    question: str
    options: List[str]
    correct: str
    explanation: str

@router.get("/api/quiz")
async def generate_quiz(subject: str, difficulty: str = "medium", topic: Optional[str] = None):
    # Base query for retrieval - we use the topic if provided, else just a general domain search
    query_text = topic if topic else f"core concepts and important definitions in {subject}"
    where_clause = {"subject": {"$eq": subject}}
    
    # Get chunks from Qdrant
    chunk_results = query_chunks(query_text, n=8, where=where_clause)
    
    if not chunk_results:
        raise HTTPException(status_code=404, detail="No relevant context found to generate a quiz for this subject.")
        
    texts = [c["text"] for c in chunk_results]
    context_text = "\n\n---\n\n".join(texts)
    
    sys_prompt = (
        "You are an expert VTU professor generating a multiple choice quiz based strictly on the provided study notes. "
        "Generate exactly 5 multiple choice questions (MCQs). "
        f"The difficulty should be {difficulty}. "
        "You MUST output valid JSON ONLY, conforming exactly to this array structure:\n"
        "[\n"
        "  {\n"
        '    "question": "...",\n'
        '    "options": ["A) ...", "B) ...", "C) ...", "D) ..."],\n'
        '    "correct": "B",\n'
        '    "explanation": "..."\n'
        "  }\n"
        "]\n"
        "Do not include any markdown formatting like ```json or other text."
    )
    
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": f"Context:\n{context_text}"}
    ]
    
    # Generate
    try:
        response_text = chat_with_context(messages)
    except Exception as e:
        print(f"[ERROR] Groq call failed in quiz: {e}")
        raise HTTPException(status_code=502, detail="AI service temporarily unavailable.")

    if not response_text or response_text.startswith("Error:"):
        raise HTTPException(status_code=502, detail=f"AI service error: {response_text}")

    # Attempt to parse JSON safely
    try:
        # Clean up any potential markdown formatting the LLM might have included
        cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
        quiz_data = json.loads(cleaned_text)
        if not isinstance(quiz_data, list) or len(quiz_data) == 0:
            raise ValueError("LLM did not return a valid list of questions.")
        return quiz_data
    except Exception as e:
        print(f"Error parsing quiz JSON from Groq: {e}\nRaw output: {response_text}")
        raise HTTPException(status_code=400, detail="Invalid JSON from LLM")
