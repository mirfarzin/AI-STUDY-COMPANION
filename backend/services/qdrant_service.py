import os, uuid
from typing import List, Dict, Optional, Any
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance, Filter, MatchValue, FieldCondition

# PUBLIC EXPORTS (for imports from other modules)
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "vtu_study_companion")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

_client = None
_embedding_model = None

def _get_embedding_fn():
    global _embedding_model
    if _embedding_model is None:
        from fastembed import TextEmbedding
        _embedding_model = TextEmbedding(model_name=EMBEDDING_MODEL)
    return _embedding_model

def get_qdrant_client():
    global _client
    if _client is None:
        url, key = os.getenv("QDRANT_URL"), os.getenv("QDRANT_API_KEY")
        if url and key:
            try:
                _client = QdrantClient(url=url, api_key=key, timeout=10)
                print("[OK] Qdrant connected")
            except Exception as e:
                print(f"[ERROR] Qdrant connection failed: {e}")
                _client = None
    return _client

def get_or_create_collection():
    client = get_qdrant_client()
    if not client: return None
    try:
        if not any(c.name == COLLECTION_NAME for c in client.get_collections().collections):
            client.create_collection(collection_name=COLLECTION_NAME, vectors_config=VectorParams(size=384, distance=Distance.COSINE))
        return client
    except Exception as e:
        print(f"[ERROR] Qdrant collection creation failed: {e}")
        return None

import hashlib

def _generate_deterministic_uuid(filename: str, chunk_index: int) -> str:
    hash_hex = hashlib.md5(f"{filename}_{chunk_index}".encode("utf-8")).hexdigest()
    # format as UUID: 8-4-4-4-12
    return f"{hash_hex[:8]}-{hash_hex[8:12]}-{hash_hex[12:16]}-{hash_hex[16:20]}-{hash_hex[20:]}"

def add_chunks(chunks: List[str], metadatas: List[Dict]) -> int:
    client = get_or_create_collection()
    if not client: return 0
    embed_fn = _get_embedding_fn()
    points = []
    for t, m, emb in zip(chunks, metadatas, embed_fn.embed(chunks)):
        filename = m.get("filename", "unknown")
        chunk_idx = m.get("chunk_index", 0)
        point_id = _generate_deterministic_uuid(filename, chunk_idx)
        points.append(PointStruct(id=point_id, vector=emb.tolist(), payload={"text": t, **m}))
    client.upsert(collection_name=COLLECTION_NAME, points=points)
    return len(points)

def semantic_search(query: str, n_results: int = 5, subject: Optional[str] = None, unit: Optional[str] = None, doc_type: Optional[str] = None) -> List[Dict]:
    client = get_qdrant_client()
    if not client: return []
    embed_fn = _get_embedding_fn()
    embeddings = list(embed_fn.embed([query]))
    q_emb = embeddings[0].tolist()
    filters = [FieldCondition(key=k, match=MatchValue(value=v)) for k, v in [("subject", subject), ("unit", unit), ("doc_type", doc_type)] if v]
    results = client.search(collection_name=COLLECTION_NAME, query_vector=q_emb, query_filter=Filter(must=filters) if filters else None, limit=n_results, with_payload=True)
    return [{"text": r.payload.get("text",""), "subject": r.payload.get("subject",""), "unit": r.payload.get("unit",""), "doc_type": r.payload.get("doc_type",""), "filename": r.payload.get("filename",""), "score": r.score} for r in results]

def get_all_chunks(where: Optional[Dict] = None) -> List[Dict]:
    client = get_qdrant_client()
    if not client: return []
    out, offset = [], None
    while True:
        pts, offset = client.scroll(collection_name=COLLECTION_NAME, limit=1000, offset=offset, with_payload=True)
        for p in pts: out.append({"text": p.payload.get("text",""), "metadata": {k:v for k,v in p.payload.items() if k!="text"}})
        if not offset: break
    return out

def get_collection_stats() -> Dict:
    client = get_qdrant_client()
    if not client: 
        return {"total_chunks": 0, "subjects": [], "doc_types": {}}
    try:
        total = client.count(collection_name=COLLECTION_NAME).count
        # Extract all unique subjects from chunks
        subjects = set()
        offset = None
        while True:
            pts, offset = client.scroll(collection_name=COLLECTION_NAME, limit=1000, offset=offset, with_payload=True)
            for p in pts:
                subj = p.payload.get("subject")
                if subj:
                    subjects.add(subj)
            if not offset:
                break
        return {
            "total_chunks": total,
            "subjects": sorted(list(subjects)),
            "doc_types": {}
        }
    except Exception as e:
        print(f"Error getting collection stats: {e}")
        return {"total_chunks": 0, "subjects": [], "doc_types": {}}

def delete_subject(subject: str) -> int:
    client = get_qdrant_client()
    if not client: return 0
    try: client.delete(collection_name=COLLECTION_NAME, points_selector=Filter(must=[FieldCondition(key="subject", match=MatchValue(value=subject))])); return 1
    except: return 0

def query_chunks(q: str, n: int = 5, where: Optional[Dict] = None) -> List[Dict]:
    subject = where.get("subject", {}).get("$eq") if where else None
    return semantic_search(q, n, subject=subject)
def list_collections() -> List[str]: c = get_qdrant_client(); return [x.name for x in c.get_collections().collections] if c else []
def delete_collection(name: str) -> bool: c = get_qdrant_client(); return c.delete_collection(collection_name=name) if c else False
