from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.qdrant_service import get_all_chunks
from services.groq_service import predict_questions

router = APIRouter()


class PredictRequest(BaseModel):
    subject: str


@router.post("/predict")
async def predict(req: PredictRequest):
    chunks = get_all_chunks(where={"subject": {"$eq": req.subject}})
    if not chunks:
        raise HTTPException(status_code=404, detail="Subject not found or contains no content.")

    # Extract just the text strings — groq_service.predict_questions expects list[str]
    texts = [c["text"] for c in chunks[:20]]

    questions = predict_questions(texts)
    return {"questions": questions, "subject": req.subject}
