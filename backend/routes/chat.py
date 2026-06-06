import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.qdrant_service import semantic_search
from services.groq_service import chat_with_context

router = APIRouter()


class ChatRequest(BaseModel):
    query: Optional[str] = None
    message: Optional[str] = None
    subject: Optional[str] = None


def _distance_to_similarity(score: float) -> int:
    return max(0, min(100, round(score * 100)))


@router.post("/chat")
async def chat(req: ChatRequest):
    user_query = (req.query or req.message or "").strip()
    if not user_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    subject = req.subject.strip() if req.subject else None

    try:
        chunk_results = semantic_search(user_query, n_results=5, subject=subject)
    except Exception as e:
        print(f"[ERROR] Qdrant semantic_search failed: {e}")
        raise HTTPException(status_code=503, detail="Vector database query failed. Please try again.")

    if not chunk_results and subject:
        try:
            chunk_results = semantic_search(user_query, n_results=5)
        except Exception:
            pass

    if not chunk_results:
        raise HTTPException(
            status_code=404,
            detail=f"No relevant content found{' for subject: ' + subject if subject else ''}. Please ensure notes are uploaded."
        )

    texts = [c["text"] for c in chunk_results]
    citations = [
        {
            "source": c.get("filename") or c.get("subject") or "Unknown Document",
            "type": "PDF Notes",
            "similarity": _distance_to_similarity(c["score"]),
        }
        for c in chunk_results
    ]

    seen: dict = {}
    for cit in citations:
        key = cit["source"]
        if key not in seen or cit["similarity"] > seen[key]["similarity"]:
            seen[key] = cit
    unique_citations = sorted(seen.values(), key=lambda x: -x["similarity"])

    context_text = "\n\n---\n\n".join(texts)
    messages = [
        {
            "role": "system",
            "content": (
                "You are a friendly and knowledgeable VTU Study Companion. "
                "Use the retrieved study notes as the primary source of information. "
                "For simple concept questions such as definitions, syntax explanations, formulas, or short doubts, "
                "provide concise answers between 100 and 200 words. Use simple language and include a short example where helpful. "
                "For exam-oriented questions, including 5-mark, 10-mark, explain, discuss, elaborate, compare, or describe questions, "
                "provide detailed VTU-style answers with proper headings and formatting. Include Definition, Explanation, Key Points, "
                "Advantages and Disadvantages (if applicable), Diagram Description (if applicable), and Conclusion. "
                "Use information from the retrieved notes first. If the notes do not contain enough information, "
                "supplement the answer using accurate academic knowledge while clearly prioritizing the uploaded notes. "
                "Do not invent facts, citations, page numbers, or sources. "
                "Be accurate, educational, well-structured, and easy to understand. "
                "Format answers using Markdown with headings, bullet points, and code blocks when appropriate."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Context from study notes:\n\n{context_text}\n\n"
                f"Question: {user_query}"
            ),
        },
    ]

    answer = chat_with_context(messages)

    if not answer or answer.startswith("Error:"):
        raise HTTPException(status_code=502, detail=f"AI service error: {answer}")

    return {
        "answer": answer,
        "subject": subject,
        "citations": unique_citations,
    }