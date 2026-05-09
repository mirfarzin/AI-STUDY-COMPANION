"""
backend/main.py
FastAPI application entry point for VTU Study Companion.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from routes import upload, chat, predict, pyq, sync
from services.chroma_service import get_collection_stats

# ── APP INIT ─────────────────────────────────────────────────────────────────
app = FastAPI(title="VTU Study Companion API", version="1.0.0")

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite default
        "http://localhost:5174",  # Vite fallback / second instance
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── ROUTES ───────────────────────────────────────────────────────────────────
app.include_router(upload.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(predict.router, prefix="/api")
app.include_router(pyq.router, prefix="/api")
app.include_router(sync.router, prefix="/api")

# ── HEALTH / STATS ───────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "message": "VTU Study Companion API is running",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/stats")
def read_stats():
    """Return ChromaDB collection stats (for debugging/monitoring)."""
    return get_collection_stats()