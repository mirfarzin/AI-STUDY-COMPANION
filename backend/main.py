"""
backend/main.py
FastAPI application entry point for VTU Study Companion.
"""
import os
import gc
from dotenv import load_dotenv

load_dotenv()

# Debug print
print(f"🔥 ENV CHECK - GROQ: {'✅' if os.getenv('GROQ_API_KEY') else '❌'} | QDRANT: {'✅' if os.getenv('QDRANT_URL') else '❌'}")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from routes import upload, chat, predict, pyq, sync

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
# No /api prefix — frontend calls routes directly
app.include_router(upload.router)
app.include_router(chat.router)
app.include_router(predict.router)
app.include_router(pyq.router)
app.include_router(sync.router)

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
    return {
        "status": "healthy",
        "timestamp": __import__("time").time(),
        "groq": "configured" if os.getenv("GROQ_API_KEY") else "missing",
        "qdrant": "configured" if os.getenv("QDRANT_URL") else "missing"
    }

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
    print("✅ Server started successfully")
    print(f"   Port: {os.getenv('PORT', 8000)}")
    print(f"   Vector DB: {VECTOR_DB_TYPE if VECTOR_DB_READY else 'NOT READY - ' + str(VECTOR_DB_ERROR)}")
    # Force garbage collection on startup to free init memory
    gc.collect()