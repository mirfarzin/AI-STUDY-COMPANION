"""
Quick ingestion script: processes all subjects from notes_raw
with explicit progress output per file.
Run: python quick_ingest.py
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv()

from pathlib import Path
import fitz  # PyMuPDF
import re
import json
import gc

# ── Setup embedding + Qdrant ──────────────────────────────────────────────────
print("Loading embedding model...")
from fastembed import TextEmbedding
embed_fn = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
print("Embedding model ready.")

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance, Filter, MatchValue, FieldCondition
import hashlib

DATA_PATH = "./qdrant_data"
COLLECTION = "vtu_study_companion"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

os.makedirs(DATA_PATH, exist_ok=True)
print(f"Opening embedded Qdrant at {DATA_PATH}")
client = QdrantClient(path=DATA_PATH)

# Create collection if missing
existing = [c.name for c in client.get_collections().collections]
if COLLECTION not in existing:
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )
    print(f"Created collection: {COLLECTION}")
else:
    count = client.count(collection_name=COLLECTION).count
    print(f"Collection exists with {count} chunks")

def chunk_text(text):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks, current = [], ""
    for sentence in sentences:
        if len(current) + len(sentence) <= CHUNK_SIZE:
            current += (" " if current else "") + sentence
        else:
            if current:
                chunks.append(current.strip())
            words = current.split()
            overlap = " ".join(words[-CHUNK_OVERLAP // 6:]) if words else ""
            current = (overlap + " " + sentence).strip() if overlap else sentence
    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if len(c) > 50]

def make_uuid(filename, idx):
    h = hashlib.md5(f"{filename}_{idx}".encode()).hexdigest()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"

def ingest_pdf(path, subject, unit="General"):
    try:
        doc = fitz.open(str(path))
        pages = []
        for pg in doc:
            t = pg.get_text("text")
            if t.strip():
                pages.append(t)
        doc.close()
        raw = "\n\n".join(pages)
        if not raw.strip():
            return 0
        chunks = chunk_text(raw)
        if not chunks:
            return 0
        metas = [{"subject": subject, "unit": unit, "filename": path.name, "chunk_index": i, "doc_type": "notes"} for i, _ in enumerate(chunks)]
        points = []
        embeddings = list(embed_fn.embed(chunks))
        for chunk, meta, emb in zip(chunks, metas, embeddings):
            pid = make_uuid(path.name, meta["chunk_index"])
            points.append(PointStruct(id=pid, vector=list(emb), payload={"text": chunk, **meta}))
        client.upsert(collection_name=COLLECTION, points=points)
        return len(points)
    except Exception as e:
        return f"ERR:{e}"

# ── Load manifest ─────────────────────────────────────────────────────────────
notes_dir = Path("notes_raw")
manifest_path = notes_dir / "manifest.json"
manifest_map = {}
if manifest_path.exists():
    for entry in json.load(open(manifest_path, encoding="utf-8")):
        manifest_map[entry["filename"]] = entry

# ── Ingest all PDFs ───────────────────────────────────────────────────────────
all_pdfs = sorted(notes_dir.rglob("*.pdf"))
total = len(all_pdfs)
total_chunks = 0
errors = 0

print(f"\nIngesting {total} PDFs...")
print("-" * 60)

for i, pdf_path in enumerate(all_pdfs, 1):
    meta = manifest_map.get(pdf_path.name, {})
    subject = meta.get("subject") or pdf_path.parent.name.replace("_", " ")
    unit = meta.get("unit", "General")
    fname = pdf_path.name.encode("ascii", errors="replace").decode("ascii")
    print(f"[{i:3d}/{total}] {subject[:25]:<25} | {fname[:40]}", end=" ", flush=True)
    result = ingest_pdf(pdf_path, subject, unit)
    if isinstance(result, str):
        print(f"ERROR: {result[:60]}")
        errors += 1
    else:
        total_chunks += result
        print(f"→ {result} chunks")
    if i % 20 == 0:
        gc.collect()

# ── Summary ───────────────────────────────────────────────────────────────────
final_count = client.count(collection_name=COLLECTION).count
print("\n" + "=" * 60)
print(f"Files processed: {total}")
print(f"Errors:          {errors}")
print(f"Chunks added:    {total_chunks}")
print(f"Total in DB:     {final_count}")
client.close()
print("Done.")
