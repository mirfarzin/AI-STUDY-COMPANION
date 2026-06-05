import math
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.qdrant_service import query_chunks, list_collections
from services.groq_service import chat_with_context

router = APIRouter()


class ChatRequest(BaseModel):
    query: str
    subject: str | None = None


def _distance_to_similarity(score: float) -> int:
    """
    Convert Qdrant cosine similarity score (0-1) → 0–100 percentage.
    Qdrant returns similarity (higher = better), not distance.
    """
    return max(0, min(100, round(score * 100)))


def _check_vector_db_ready():
    """Check if vector database is initialized, raise error if not."""
    try:
        from main import VECTOR_DB_READY, VECTOR_DB_ERROR
        if not VECTOR_DB_READY:
            raise HTTPException(
                status_code=503,
                detail=f"Qdrant not available: {VECTOR_DB_ERROR}. Please configure QDRANT_URL and QDRANT_API_KEY environment variables."
            )
    except ImportError:
        pass  # Fallback if import fails


@router.post("/chat")
async def chat(req: ChatRequest):
    _check_vector_db_ready()

    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # Normalize subject name: strip whitespace
    subject = req.subject.strip() if req.subject else None
    where_clause = {"subject": {"$eq": subject}} if subject else None

    try:
        chunk_results = query_chunks(req.query, n=5, where=where_clause)
    except Exception as e:
        print(f"[ERROR] Qdrant query failed: {e}")
        raise HTTPException(status_code=503, detail="Vector database query failed. Please try again.")

    if not chunk_results:
        # Fallback: try without subject filter
        if subject:
            try:
                chunk_results = query_chunks(req.query, n=5, where=None)
            except Exception:
                pass
        if not chunk_results:
            raise HTTPException(
                status_code=404,
                detail=f"No relevant content found{' for subject: ' + subject if subject else ''}. Please ensure notes are uploaded."
            )

    # Separate texts for LLM and build citations
    texts = [c["text"] for c in chunk_results]

    citations = [
        {
            "source": c.get("filename") or c.get("subject") or "Unknown Document",
            "type": "PDF Notes",
            "similarity": _distance_to_similarity(c["score"]),
        }
        for c in chunk_results
    ]

    # Deduplicate citations by source + keep the highest-similarity one
    seen: dict[str, dict] = {}
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
                "You are a helpful VTU study assistant. Answer questions based on the provided study notes context. "
                "Be concise, accurate, and cite the subject when relevant."
            ),
        },
        {
            "role": "user",
            "content": f"Context from study notes:\n\n{context_text}\n\nQuestion: {req.query}",
        },
    ]

    try:
        answer = chat_with_context(messages)
    except Exception as e:
        print(f"[ERROR] Groq LLM call failed: {e}")
        raise HTTPException(status_code=502, detail="AI service temporarily unavailable. Please try again.")

    if not answer or answer.startswith("Error:"):
        raise HTTPException(status_code=502, detail=f"AI service error: {answer}")

    return {
        "answer": answer,
        "subject": subject,
        "citations": unique_citations,
    }
