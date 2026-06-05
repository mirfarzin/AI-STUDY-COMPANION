"""
backend/main.py
FastAPI application entry point for VTU Study Companion.
"""
import os
import gc
from dotenv import load_dotenv

load_dotenv()

# Debug print (ASCII-safe for Windows console compatibility)
print(f"[ENV] GROQ: {'OK' if os.getenv('GROQ_API_KEY') else 'MISSING'} | QDRANT: {'OK' if os.getenv('QDRANT_URL') else 'MISSING'}")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from routes import upload, chat, predict, pyq, sync, quiz, weak_topics

# ── QDRANT CLOUD INITIALIZATION ───────────────────────────────────────────────
VECTOR_DB_READY = False
VECTOR_DB_TYPE = "Not initialized"
VECTOR_DB_ERROR = None

try:
    from services.qdrant_service import get_qdrant_client, get_collection_stats
    # get_qdrant_client() reads QDRANT_URL and QDRANT_API_KEY from env at call time
    _qdrant_url = os.getenv("QDRANT_URL")
    _qdrant_key = os.getenv("QDRANT_API_KEY")
    print(f"[INIT] QDRANT_URL={'set' if _qdrant_url else 'MISSING'}, QDRANT_API_KEY={'set' if _qdrant_key else 'MISSING'}")

    if _qdrant_url and _qdrant_key:
        if get_qdrant_client():
            VECTOR_DB_READY = True
            VECTOR_DB_TYPE = "Qdrant Cloud"
        else:
            VECTOR_DB_ERROR = "Failed to connect to Qdrant Cloud"
    else:
        VECTOR_DB_ERROR = "Qdrant credentials (QDRANT_URL, QDRANT_API_KEY) not configured"
except Exception as e:
    VECTOR_DB_READY = False
    VECTOR_DB_ERROR = f"Failed to initialize Qdrant: {str(e)}"

# ── APP INIT ─────────────────────────────────────────────────────────────────
app = FastAPI(title="VTU Study Companion API", version="1.0.0")

# ── CORS ─────────────────────────────────────────────────────────────────────
# Allow both local dev and production frontend origins
FRONTEND_URLS = os.getenv("FRONTEND_URLS", "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174")
allowed_origins = [u.strip() for u in FRONTEND_URLS.split(",") if u.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now (Railway + Vercel)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── ROUTES ───────────────────────────────────────────────────────────────────
# Include all routers with /api prefix
app.include_router(upload.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(predict.router, prefix="/api")
app.include_router(pyq.router, prefix="/api")
app.include_router(sync.router, prefix="/api")
app.include_router(quiz.router, prefix="/api")
app.include_router(weak_topics.router, prefix="/api")

# ── HEALTH / STATS ───────────────────────────────────────────────────────────
@app.get("/ping")
def ping():
    """Simple health check - always returns 200 if server is running"""
    return {"status": "pong"}

@app.get("/")
def root():
    return {
        "message": "VTU Study Companion API is running",
        "status": "healthy" if os.getenv("GROQ_API_KEY") else "degraded",
        "groq_configured": bool(os.getenv("GROQ_API_KEY")),
        "qdrant_configured": bool(os.getenv("QDRANT_URL")),
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
def health():
    groq_ok = bool(os.getenv("GROQ_API_KEY"))
    qdrant_ok = bool(os.getenv("QDRANT_URL") and os.getenv("QDRANT_API_KEY"))
    status = "healthy" if (groq_ok and qdrant_ok) else "degraded"
    return {"status": status, "ready": status == "healthy", "groq": "configured" if groq_ok else "missing", "qdrant": "configured" if qdrant_ok else "missing"}

@app.get("/stats")
def read_stats():
    """Return vector database collection stats (for debugging/monitoring)."""
    if not VECTOR_DB_READY:
        raise HTTPException(
            status_code=503,
            detail=f"Qdrant not initialized: {VECTOR_DB_ERROR}. Please configure QDRANT_URL and QDRANT_API_KEY environment variables."
        )
    try:
        return get_collection_stats()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve stats: {str(e)}"
        )

@app.on_event("startup")
async def startup():
    import asyncio
    print("Server started successfully")
    print(f"   Port: {os.getenv('PORT', 8080)}")
    print(f"   Vector DB: {VECTOR_DB_TYPE if VECTOR_DB_READY else 'NOT READY - ' + str(VECTOR_DB_ERROR)}")
    gc.collect()

    # Auto-ingest if Qdrant is empty and notes_raw folder exists
    asyncio.create_task(_auto_ingest_if_empty())


async def _auto_ingest_if_empty():
    """Background task: auto-ingest PDFs from notes_raw if Qdrant collection is empty."""
    import asyncio
    from pathlib import Path
    await asyncio.sleep(3)  # Let server finish starting

    notes_dir = Path("notes_raw")
    if not notes_dir.exists():
        print("[STARTUP] notes_raw/ not found — skipping auto-ingestion.")
        return

    try:
        from services.qdrant_service import get_collection_stats, get_or_create_collection
        get_or_create_collection()  # Ensure collection exists
        stats = get_collection_stats()
        total = stats.get("total_chunks", 0)
        if total > 0:
            print(f"[STARTUP] Qdrant already has {total} chunks — skipping auto-ingestion.")
            return

        print("[STARTUP] Qdrant is empty. Starting auto-ingestion from notes_raw/ ...")
        from services.pdf_service import ingest_folder
        result = ingest_folder(notes_dir)
        print(f"[STARTUP] Auto-ingestion complete: {result['files_processed']} files, {result['total_chunks']} chunks, {len(result['errors'])} errors.")
    except Exception as e:
        print(f"[STARTUP] Auto-ingestion failed: {e}")


# ── DEFAULT SUBJECTS ENDPOINT ────────────────────────────────────────────────
DEFAULT_SUBJECTS = [
    "CAED",
    "Chemistry",
    "Communication English",
    "Constitution of India",
    "Design Thinking",
    "ESC",
    "ETC",
    "Kannada Kali Manasu",
    "Mathematics ChemistryCycle",
    "Mathematics PhysicsCycle",
    "PLC",
    "Physics",
    "Principles of Programming C",
    "Professional Writing English"
]

@app.get("/subjects")
def get_subjects():
    """Get all available subjects from Qdrant or return defaults"""
    try:
        stats = get_collection_stats()
        subjects = stats.get("subjects", [])
        if subjects:
            return {"subjects": subjects}
    except Exception as e:
        print(f"Error fetching subjects from Qdrant: {e}")
    
    # Return default subjects if Qdrant is not available
    return {"subjects": DEFAULT_SUBJECTS}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)