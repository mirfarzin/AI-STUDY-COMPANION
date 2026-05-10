"""
backend/services/pdf_service.py
PDF ingestion pipeline:
  PDF file → extract text → chunk → embed → store in Qdrant
Also handles folder-level batch ingestion (used by sync route).
"""

import gc
import json
import re
import uuid
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
from services.qdrant_service import (
    get_or_create_collection,
    add_chunks as qdrant_add_chunks,
    get_all_chunks,
    COLLECTION_NAME,
)

# ── CONFIG ────────────────────────────────────────────────────────────────────
CHUNK_SIZE    = 800    # characters per chunk
CHUNK_OVERLAP = 150    # overlap between chunks


# ── TEXT EXTRACTION ───────────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_path_or_bytes) -> str:
    """Extract raw text from a PDF using PyMuPDF.
    
    Args:
        pdf_path_or_bytes: Either a file path (str/Path) or raw bytes content.
    """
    if isinstance(pdf_path_or_bytes, (str, Path)):
        path = Path(pdf_path_or_bytes)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")
        doc = fitz.open(str(path))
    else:
        # Handle raw bytes (from upload route)
        doc = fitz.open(stream=pdf_path_or_bytes, filetype="pdf")
    
    pages = []
    for page_num, page in enumerate(doc):
        text = page.get_text("text")
        if text.strip():
            pages.append(f"[Page {page_num + 1}]\n{text}")
    doc.close()
    return "\n\n".join(pages)


# ── CHUNKING ──────────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE,
               overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks by sentence boundary."""
    # Split on sentence-ending punctuation
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks, current = [], ""
    for sentence in sentences:
        if len(current) + len(sentence) <= chunk_size:
            current += (" " if current else "") + sentence
        else:
            if current:
                chunks.append(current.strip())
            # Start new chunk with overlap
            words = current.split()
            overlap_text = " ".join(words[-overlap // 6:]) if words else ""
            current = overlap_text + " " + sentence if overlap_text else sentence
    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if len(c) > 50]  # filter trivially short chunks


# ── INGEST SINGLE FILE ────────────────────────────────────────────────────────

def ingest_pdf(
    pdf_path: str | Path,
    subject: str,
    unit: str = "General",
    doc_type: str = "notes",    # "notes" | "pyq"
    source_url: str = "",
    force: bool = False,
) -> int:
    """
    Extract → chunk → embed → store one PDF into Qdrant.
    Returns number of chunks stored.
    
    Args:
        force: If True, re-ingest even if PDF already exists in collection.
    """
    path = Path(pdf_path)
    
    # Ensure Qdrant collection exists
    get_or_create_collection()

    # Check if already ingested (by source path)
    if not force:
        try:
            existing = get_all_chunks(where={"source_path": {"$eq": str(path)}})
            if existing:
                print(f"  [SKIP] Already indexed: {path.name}")
                return 0
        except Exception:
            pass  # If check fails, proceed with ingestion

    print(f"  [INGEST] {path.name} | {subject} | {unit}")
    raw_text = extract_text_from_pdf(path)
    if not raw_text.strip():
        print(f"  [WARN]  No text extracted from {path.name} (may be scanned/image PDF)")
        return 0

    chunks = chunk_text(raw_text)
    if not chunks:
        return 0

    # Build metadata for each chunk
    metas = []
    for i, chunk in enumerate(chunks):
        metas.append({
            "subject":     subject,
            "unit":        unit,
            "doc_type":    doc_type,
            "filename":    path.name,
            "source_path": str(path),
            "chunk_index": i,
            "total_chunks": len(chunks),
        })

    # Add to Qdrant using the service function
    added = qdrant_add_chunks(COLLECTION_NAME, chunks, metas)
    print(f"  [OK]    {added} chunks → Qdrant Cloud")
    
    # Free memory after ingestion
    gc.collect()
    
    return len(chunks)


# ── INGEST FOLDER ─────────────────────────────────────────────────────────────

def ingest_folder(folder: str | Path, doc_type: str = "notes") -> dict:
    """
    Walk a folder structured as:
      folder/
        Subject_Name/
          unit1.pdf
          unit2.pdf
    Load manifest.json if present for richer metadata.
    """
    folder = Path(folder)
    manifest_path = folder / "manifest.json"
    manifest_map: dict[str, dict] = {}

    if manifest_path.exists():
        with open(manifest_path) as f:
            for entry in json.load(f):
                manifest_map[entry["filename"]] = entry

    total_chunks = 0
    total_files  = 0
    errors       = []

    for pdf_path in sorted(folder.rglob("*.pdf")):
        meta = manifest_map.get(pdf_path.name, {})
        subject = meta.get("subject") or pdf_path.parent.name.replace("_", " ")
        unit    = meta.get("unit", "General")
        url     = meta.get("url", "")

        try:
            chunks = ingest_pdf(
                pdf_path=pdf_path,
                subject=subject,
                unit=unit,
                doc_type=doc_type,
                source_url=url,
                force=True,  # Folder ingestion always forces re-ingest
            )
            total_chunks += chunks
            total_files  += 1
        except Exception as e:
            errors.append({"file": str(pdf_path), "error": str(e)})
            print(f"  [ERROR] {pdf_path.name}: {e}")

    # Clean up memory after batch ingestion
    gc.collect()

    return {
        "files_processed": total_files,
        "total_chunks":    total_chunks,
        "errors":          errors,
    }


# ── STANDALONE TEST ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result = ingest_pdf(
            pdf_path=sys.argv[1],
            subject=sys.argv[2] if len(sys.argv) > 2 else "Unknown",
            unit=sys.argv[3] if len(sys.argv) > 3 else "General",
            force="--force" in sys.argv or "-f" in sys.argv,
        )
        print(f"Ingested {result} chunks.")
    else:
        print("Usage: python pdf_service.py <path.pdf> [subject] [unit] [--force]")