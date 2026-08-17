import re

from fastapi import APIRouter, UploadFile, File, HTTPException

from backend.services.pdf_service import extract_text_from_pdf, chunk_text
from backend.lib.clients.qdrant import (
    add_chunks,
    list_collections,
    delete_collection,
)

router = APIRouter()


def _check_vector_db_ready():
    """Check if vector database is initialized, raise error if not."""
    try:
        from backend.main import VECTOR_DB_READY, VECTOR_DB_ERROR
        if not VECTOR_DB_READY:
            raise HTTPException(
                status_code=503,
                detail=f"Qdrant not available: {VECTOR_DB_ERROR}. Cannot upload documents. Please configure QDRANT_URL and QDRANT_API_KEY environment variables."
            )
    except ImportError:
        pass  # Fallback if import fails


def _sanitize(name: str) -> str:
    """Make a valid ChromaDB collection name."""

    base = name.rsplit(".", 1)[0]

    clean = re.sub(r"[^a-zA-Z0-9-]", "-", base)
    clean = re.sub(r"-+", "-", clean).strip("-")

    clean = clean[:63]

    if len(clean) < 3:
        clean = clean + "-doc"

    return clean.lower()


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    _check_vector_db_ready()

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    content = await file.read()

    text = extract_text_from_pdf(content)

    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail="Could not extract text from this PDF.",
        )

    chunks = chunk_text(text)

    doc_id = _sanitize(file.filename)

    metadatas = [
        {
            "subject": "Uploaded",
            "unit": "General",
            "doc_type": "notes",
            "filename": file.filename,
            "chunk_index": i,
        }
        for i in range(len(chunks))
    ]
    add_chunks(chunks, metadatas)

    return {
        "doc_id": doc_id,
        "filename": file.filename,
        "chunks": len(chunks),
        "message": "PDF ingested successfully",
    }


@router.get("/documents")
async def get_documents():

    return {
        "documents": list_collections()
    }

from backend.lib.clients.qdrant import get_collection_stats, delete_subject




@router.delete("/subject/{subject}")
async def delete_subject_route(subject: str):

    deleted_count = delete_subject(subject)

    return {
        "message": f"Subject '{subject}' deleted. ({deleted_count} chunks)",
        "deleted_count": deleted_count
    }