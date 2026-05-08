import math
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.chroma_service import query_chunks, list_collections
from services.groq_service import chat_with_context

router = APIRouter()


class ChatRequest(BaseModel):
    query: str
    subject: str | None = None


def _distance_to_similarity(distance: float) -> int:
    """
    Convert ChromaDB L2 distance → 0–100 similarity score.
    Uses a simple exponential decay: sim = 100 * exp(-distance / 2).
    Lower L2 distance = higher similarity.
    """
    return round(100 * math.exp(-distance / 2))


@router.post("/chat")
async def chat(req: ChatRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    where_clause = {"subject": {"$eq": req.subject}} if req.subject else None

    chunk_results = query_chunks(req.query, n_results=5, where=where_clause)

    if not chunk_results:
        raise HTTPException(status_code=404, detail="No relevant content found for this subject.")

    # Separate texts for LLM and build citations
    texts = [c["text"] for c in chunk_results]

    citations = [
        {
            "source": c.get("metadata", {}).get("filename", "Unknown Document"),
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

    answer = chat_with_context(req.query, texts)

    return {
        "answer": answer,
        "subject": req.subject,
        "citations": unique_citations,
    }
