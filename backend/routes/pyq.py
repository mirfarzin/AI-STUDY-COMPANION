from fastapi import APIRouter, HTTPException, Query
from backend.services.pyq_service import analyze_pyqs

router = APIRouter()


@router.get("/predict-questions")
async def predict_questions(
    threshold: float = Query(
        default=0.78,
        ge=0.5,
        le=1.0,
        description="Cosine similarity threshold for grouping similar questions (0.5–1.0).",
    )
):
    """
    Analyze all uploaded PYQ PDFs and return questions ranked by frequency.

    Each item in the response contains:
    - **question**: the canonical question text
    - **frequency**: number of unique PDFs it appeared in
    - **years**: list of years/sources it was found in
    - **probability**: High (freq≥3) | Medium (freq=2) | Low (freq=1)
    """
    results = analyze_pyqs(similarity_threshold=threshold)

    if not results:
        raise HTTPException(
            status_code=404,
            detail="No question-like content found. Upload PYQ PDFs with question text first.",
        )

    high   = [r for r in results if r["probability"] == "High"]
    medium = [r for r in results if r["probability"] == "Medium"]
    low    = [r for r in results if r["probability"] == "Low"]

    return {
        "total": len(results),
        "summary": {"High": len(high), "Medium": len(medium), "Low": len(low)},
        "questions": results,
    }

from pydantic import BaseModel
from backend.lib.clients.qdrant import query_chunks
from backend.lib.clients.groq import chat_with_context
from backend.lib.prompts.templates import PYQ_SYSTEM_PROMPT

class PYQRequest(BaseModel):
    question: str
    subject: str = None

@router.post("/pyq")
async def solve_pyq(req: PYQRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    where_clause = {"subject": {"$eq": req.subject}} if req.subject else None
    
    # Top-k=5 chunks
    chunk_results = query_chunks(req.question, n=5, where=where_clause)
    
    if not chunk_results:
        raise HTTPException(status_code=404, detail="No relevant context found for this question.")
        
    texts = [c["text"] for c in chunk_results]
    
    sources = [
        {
            "subject": c.get("subject", "Unknown"),
            "filename": c.get("filename", "Unknown Document"),
            "page": c.get("page", 1),
            "excerpt": c["text"][:100] + "..." if len(c["text"]) > 100 else c["text"]
        }
        for c in chunk_results
    ]
    
    # Deduplicate sources based on filename and excerpt
    seen = set()
    unique_sources = []
    for s in sources:
        key = f"{s['filename']}_{s['excerpt']}"
        if key not in seen:
            seen.add(key)
            unique_sources.append(s)
    
    context_text = "\n\n---\n\n".join(texts)
    messages = [
        {
            "role": "system",
            "content": PYQ_SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": f"Context:\n{context_text}\n\nQuestion: {req.question}"
        }
    ]
    
    answer = chat_with_context(messages)
    
    if not answer or answer.startswith("Error:"):
        raise HTTPException(status_code=502, detail=f"AI service error: {answer}")
    
    return {
        "answer": answer,
        "sources": unique_sources,
        "confidence": "High" if len(chunk_results) >= 3 else "Medium"
    }
