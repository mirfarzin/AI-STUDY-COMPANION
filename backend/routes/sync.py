"""
backend/routes/sync.py
Triggers scraper → PDF ingestion → ChromaDB indexing pipeline.
POST /sync/notes   → scrape ritnotebook.in + ingest
GET  /sync/status  → returns manifest + chroma stats
"""

import json
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

from backend.services.scraper_service import scrape_ritnotebook
from backend.services.pdf_service import ingest_folder
from backend.lib.clients.qdrant import get_collection_stats

router = APIRouter(prefix="/sync", tags=["sync"])

NOTES_DIR    = Path("notes_raw")
MANIFEST     = NOTES_DIR / "manifest.json"
_sync_status = {"running": False, "last": None, "error": None}


def _run_sync():
    global _sync_status
    _sync_status = {"running": True, "last": None, "error": None}
    try:
        print("🔄 Sync started: scraping ritnotebook.in ...")
        manifest = scrape_ritnotebook(NOTES_DIR)

        print(f"📥 Ingesting {len(manifest)} files into ChromaDB ...")
        ingest_folder(NOTES_DIR, doc_type="notes")

        _sync_status = {
            "running": False,
            "last": {
                "files_scraped": len(manifest),
                "subjects": list({m["subject"] for m in manifest}),
            },
            "error": None,
        }
        print("✅ Sync complete.")
    except Exception as e:
        _sync_status = {"running": False, "last": None, "error": str(e)}
        print(f"❌ Sync error: {e}")


@router.post("/notes")
async def sync_notes(background_tasks: BackgroundTasks):
    """Trigger a background scrape + ingest of ritnotebook.in notes."""
    if _sync_status["running"]:
        raise HTTPException(status_code=409, detail="Sync already running.")
    background_tasks.add_task(_run_sync)
    return {"message": "Sync started in background. Poll /sync/status for progress."}


@router.get("/status")
async def sync_status():
    """Returns current sync status + ChromaDB collection stats."""
    manifest = []
    if MANIFEST.exists():
        with open(MANIFEST) as f:
            manifest = json.load(f)

    return {
        "sync": _sync_status,
        "manifest_count": len(manifest),
        "subjects": list({m["subject"] for m in manifest}),
        "chroma": get_collection_stats(),
    }