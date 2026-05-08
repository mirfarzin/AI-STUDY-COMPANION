from fastapi import APIRouter, HTTPException, Query
from services.pyq_service import analyze_pyqs

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
