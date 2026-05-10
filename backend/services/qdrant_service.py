"""
backend/services/qdrant_service.py
Qdrant vector database service for VTU Study Companion.
Handles embedding, storage, retrieval, and collection management.
"""

import os
import uuid
from typing import List, Dict, Optional, Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    PointStruct, VectorParams, Distance, Filter, MatchValue, FieldCondition
)

# ── CONFIG ──────────────────────────────────────────────────────────────────
_client: Optional[QdrantClient] = None
_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "vtu_study_companion")
_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

# Lazy-load embedding model to avoid heavy imports on startup
_embedding_model = None

def _get_embedding_fn():
    global _embedding_model
    if _embedding_model is None:
        try:
            from fastembed import TextEmbedding
            _embedding_model = TextEmbedding(model_name=_EMBEDDING_MODEL)
        except ImportError:
            raise RuntimeError(
                "fastembed not installed. Run: pip install fastembed"
            )
    return _embedding_model

def get_qdrant_client() -> Optional[QdrantClient]:
    """Initialize and return Qdrant client singleton."""
    global _client
    if _client is None:
        url = os.getenv("QDRANT_URL")
        api_key = os.getenv("QDRANT_API_KEY")
        if url and api_key:
            try:
                _client = QdrantClient(url=url, api_key=api_key, timeout=10)
                print(f"✅ Qdrant connected: {url}")
            except Exception as e:
                print(f"❌ Qdrant connection failed: {e}")
                _client = None
        else:
            print("⚠️ Qdrant disabled - missing QDRANT_URL or QDRANT_API_KEY")
    return _client

def get_or_create_collection() -> Optional[QdrantClient]:
    """Ensure collection exists with correct schema. Returns client or None."""
    client = get_qdrant_client()
    if not client:
        return None
    try:
        collections = client.get_collections()
        exists = any(c.name == _COLLECTION_NAME for c in collections.collections)
        if not exists:
            print(f"📦 Creating collection: {_COLLECTION_NAME}")
            client.create_collection(
                collection_name=_COLLECTION_NAME,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )
            client.create_payload_index(
                collection_name=_COLLECTION_NAME,
                field_name="subject",
                field_schema="keyword"
            )
        return client
    except Exception as e:
        print(f"❌ Collection setup failed: {e}")
        return None

def add_chunks(chunks: List[str], metadatas: List[Dict]) -> int:
    """Embed and upsert chunks into Qdrant."""
    client = get_or_create_collection()
    if not client:
        return 0

    embed_fn = _get_embedding_fn()
    embeddings = list(embed_fn.embed(chunks))

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=emb.tolist(),
            payload={"text": text, **meta}
        )
        for text, meta, emb in zip(chunks, metadatas, embeddings)
    ]

    client.upsert(collection_name=_COLLECTION_NAME, points=points)
    return len(points)

def semantic_search(
    query: str,
    n_results: int = 5,
    subject: Optional[str] = None,
    unit: Optional[str] = None,
    doc_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Search Qdrant with optional metadata filters."""
    client = get_qdrant_client()
    if not client:
        return []

    embed_fn = _get_embedding_fn()
    query_embedding = list(embed_fn.embed([query]))[0].tolist()

    filter_conditions = []
    if subject: filter_conditions.append(FieldCondition(key="subject", match=MatchValue(value=subject)))
    if unit: filter_conditions.append(FieldCondition(key="unit", match=MatchValue(value=unit)))
    if doc_type: filter_conditions.append(FieldCondition(key="doc_type", match=MatchValue(value=doc_type)))

    search_filter = Filter(must=filter_conditions) if filter_conditions else None

    results = client.search(
        collection_name=_COLLECTION_NAME,
        query_vector=query_embedding,
        query_filter=search_filter,
        limit=n_results,
        with_payload=True
    )

    return [
        {
            "text": r.payload.get("text", ""),
            "subject": r.payload.get("subject", ""),
            "unit": r.payload.get("unit", ""),
            "doc_type": r.payload.get("doc_type", ""),
            "filename": r.payload.get("filename", ""),
            "score": r.score
        }
        for r in results
    ]

def get_all_chunks(where: Optional[Dict] = None) -> List[Dict]:
    """Retrieve chunks (paginated scroll for safety)."""
    client = get_qdrant_client()
    if not client:
        return []

    output = []
    points, next_offset = client.scroll(
        collection_name=_COLLECTION_NAME,
        limit=1000,
        with_payload=True
    )
    while points:
        for p in points:
            output.append({
                "text": p.payload.get("text", ""),
                "metadata": {k: v for k, v in p.payload.items() if k != "text"}
            })
        if next_offset is None:
            break
        points, next_offset = client.scroll(
            collection_name=_COLLECTION_NAME,
            limit=1000,
            offset=next_offset,
            with_payload=True
        )
    return output

def get_collection_stats() -> Dict:
    """Return collection statistics."""
    client = get_qdrant_client()
    if not client:
        return {"total_chunks": 0, "subjects": [], "doc_types": {}}
    try:
        count = client.count(collection_name=_COLLECTION_NAME).count
        return {"total_chunks": count, "subjects": [], "doc_types": {}}
    except Exception:
        return {"total_chunks": 0, "subjects": [], "doc_types": {}}

def delete_subject(subject: str) -> int:
    """Delete all chunks for a given subject using Qdrant native filtering."""
    client = get_qdrant_client()
    if not client:
        return 0
    try:
        client.delete(
            collection_name=_COLLECTION_NAME,
            points_selector=Filter(must=[FieldCondition(key="subject", match=MatchValue(value=subject))])
        )
        return 1
    except Exception as e:
        print(f"❌ Delete failed: {e}")
        return 0

def query_chunks(query: str, n_results: int = 5, where: Optional[Dict] = None) -> List[Dict]:
    """Alias for semantic_search for backward compatibility."""
    return semantic_search(query, n_results)

def list_collections() -> List[str]:
    client = get_qdrant_client()
    if not client:
        return []
    return [c.name for c in client.get_collections().collections]

def delete_collection(name: str) -> bool:
    client = get_qdrant_client()
    if not client:
        return False
    try:
        client.delete_collection(collection_name=name)
        return True
    except Exception:
        return False