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
                print("✅ Qdrant connected")
            except: _client = None
    return _client

def get_or_create_collection():
    client = get_qdrant_client()
    if not client: return None
    try:
        if not any(c.name == COLLECTION_NAME for c in client.get_collections().collections):
            client.create_collection(collection_name=COLLECTION_NAME, vectors_config=VectorParams(size=384, distance=Distance.COSINE))
        return client
    except: return None

def add_chunks(chunks: List[str], metadatas: List[Dict]) -> int:
    client = get_or_create_collection()
    if not client: return 0
    embed_fn = _get_embedding_fn()
    points = [PointStruct(id=str(uuid.uuid4()), vector=emb.tolist(), payload={"text": t, **m}) for t, m, emb in zip(chunks, metadatas, embed_fn.embed(chunks))]
    client.upsert(collection_name=COLLECTION_NAME, points=points)
    return len(points)

def semantic_search(query: str, n_results: int = 5, subject: Optional[str] = None, unit: Optional[str] = None, doc_type: Optional[str] = None) -> List[Dict]:
    client = get_qdrant_client()
    if not client: return []
    embed_fn = _get_embedding_fn()
    q_emb = embed_fn.embed([query])[0].tolist()
    filters = [FieldCondition(key=k, match=MatchValue(v)) for k, v in [("subject", subject), ("unit", unit), ("doc_type", doc_type)] if v]
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
    if not client: return {"total_chunks": 0, "subjects": [], "doc_types": {}}
    try: return {"total_chunks": client.count(collection_name=COLLECTION_NAME).count, "subjects": [], "doc_types": {}}
    except: return {"total_chunks": 0, "subjects": [], "doc_types": {}}

def delete_subject(subject: str) -> int:
    client = get_qdrant_client()
    if not client: return 0
    try: client.delete(collection_name=COLLECTION_NAME, points_selector=Filter(must=[FieldCondition(key="subject", match=MatchValue(value=subject))])); return 1
    except: return 0

def query_chunks(q: str, n: int = 5, where: Optional[Dict] = None) -> List[Dict]: return semantic_search(q, n)
def list_collections() -> List[str]: c = get_qdrant_client(); return [x.name for x in c.get_collections().collections] if c else []
def delete_collection(name: str) -> bool: c = get_qdrant_client(); return c.delete_collection(collection_name=name) if c else False
