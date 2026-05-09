"""
backend/main.py
FastAPI application entry point for VTU Study Companion.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from routes import upload, chat, predict, pyq, sync
from services.qdrant_service import get_collection_stats

# ── APP INIT ─────────────────────────────────────────────────────────────────
app = FastAPI(title="VTU Study Companion API", version="1.0.0")

# ── CORS ─────────────────────────────────────────────────────────────────────
# Allow both local dev and production frontend origins
FRONTEND_URLS = os.getenv("FRONTEND_URLS", "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174")
allowed_origins = [u.strip() for u in FRONTEND_URLS.split(",") if u.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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