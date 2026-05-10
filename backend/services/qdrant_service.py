"""
Qdrant Cloud service - replacement for ChromaDB
Handles all vector database operations for the VTU Study Companion
"""
import os
import gc
from typing import Optional, List, Dict
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from dotenv import load_dotenv

load_dotenv()

COLLECTION_NAME = "vtu_study_companion"
VECTOR_SIZE = 384  # all-MiniLM-L6-v2 output dimension

_client: Optional[QdrantClient] = None
_embedding_model = None


def _get_embedding_model():
    """Lazy-load the sentence-transformers embedding model"""
    global _embedding_model

    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            print("[QDRANT] Embedding model loaded: all-MiniLM-L6-v2")
        except Exception as e:
            print(f"[QDRANT ERROR] Failed to load embedding model: {e}")
            return None

    return _embedding_model


def get_client() -> Optional[QdrantClient]:
    """Get or create Qdrant client (reads env vars lazily at call time)"""
    global _client

    if _client is None:
        url = os.getenv("QDRANT_URL")
        api_key = os.getenv("QDRANT_API_KEY")
        if url and api_key:
            _client = QdrantClient(url=url, api_key=api_key)
            print(f"[QDRANT] Connected to {url}")
            # Ensure collection exists
            _ensure_collection()
        else:
            print(f"[QDRANT WARNING] Missing credentials: QDRANT_URL={'set' if url else 'MISSING'}, QDRANT_API_KEY={'set' if api_key else 'MISSING'}")

    return _client


def _ensure_collection():
    """Ensure collection exists in Qdrant Cloud"""
    if not _client:
        return

    try:
        # Try to get collection info - if it doesn't exist, this will fail
        _client.get_collection(COLLECTION_NAME)
    except Exception:
        # Collection doesn't exist, create it
        try:
            _client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config={"size": VECTOR_SIZE, "distance": "Cosine"},
            )
            print(f"[QDRANT] Created collection: {COLLECTION_NAME}")
        except Exception as e:
            print(f"[QDRANT WARNING] Could not create collection: {e}")


def _get_embedding(text: str) -> List[float]:
    """Get embedding for text using sentence-transformers"""
    try:
        model = _get_embedding_model()
        if model is None:
            return [0.0] * VECTOR_SIZE
        embedding = model.encode(text, show_progress_bar=False)
        return embedding.tolist()
    except Exception as e:
        print(f"[QDRANT ERROR] Failed to get embedding: {e}")
        return [0.0] * VECTOR_SIZE


def _get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Get embeddings for multiple texts at once (much faster than one-by-one)"""
    try:
        model = _get_embedding_model()
        if model is None:
            return [[0.0] * VECTOR_SIZE for _ in texts]
        embeddings = model.encode(texts, show_progress_bar=False, batch_size=64)
        return [e.tolist() for e in embeddings]
    except Exception as e:
        print(f"[QDRANT ERROR] Failed to get batch embeddings: {e}")
        return [[0.0] * VECTOR_SIZE for _ in texts]


def get_or_create_collection():
    """Compatibility function - just ensures collection exists"""
    get_client()
    _ensure_collection()
    return True


def add_chunks(
    collection_name: str,
    chunks: List[str],
    metadatas: List[Dict] = None,
) -> int:
    """Add chunks to Qdrant Cloud"""
    client = get_client()
    if not client:
        print("[QDRANT ERROR] Client not initialized")
        return 0

    if metadatas is None:
        metadatas = [{} for _ in chunks]

    # Batch encode all texts at once (much faster)
    all_embeddings = _get_embeddings_batch(chunks)

    # Build points
    points = []
    for chunk, meta, embedding in zip(chunks, metadatas, all_embeddings):
        try:
            point_id = uuid.uuid4().int % (2**63)  # Qdrant requires uint64 IDs

            points.append({
                "id": point_id,
                "vector": embedding,
                "payload": {
                    "text": chunk,
                    "subject": meta.get("subject", ""),
                    "unit": meta.get("unit", ""),
                    "doc_type": meta.get("doc_type", ""),
                    "filename": meta.get("filename", ""),
                    "source_path": meta.get("source_path", ""),
                }
            })
        except Exception as e:
            print(f"[QDRANT ERROR] Failed to process chunk: {e}")
            continue

    if not points:
        return 0

    try:
        # Add in batches
        batch_size = 100
        total_added = 0

        for i in range(0, len(points), batch_size):
            batch = points[i:i+batch_size]
            client.upsert(
                collection_name=COLLECTION_NAME,
                points=batch,
            )
            total_added += len(batch)

        # Free memory after large ingestion
        if total_added > 500:
            gc.collect()

        return total_added
    except Exception as e:
        print(f"[QDRANT ERROR] Failed to add chunks: {e}")
        return 0


def query_chunks(
    query: str,
    n_results: int = 5,
    where: dict = None,
) -> List[Dict]:
    """Query chunks from Qdrant Cloud"""
    client = get_client()
    if not client:
        return []

    try:
        query_embedding = _get_embedding(query)

        # Build filter from where clause
        filter_condition = None
        if where:
            filter_condition = _build_filter(where)

        results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_embedding,
            limit=n_results,
            query_filter=filter_condition,
        )

        output = []
        for result in results:
            output.append({
                "text": result.payload.get("text", ""),
                "metadata": {
                    "subject": result.payload.get("subject", ""),
                    "unit": result.payload.get("unit", ""),
                    "doc_type": result.payload.get("doc_type", ""),
                    "filename": result.payload.get("filename", ""),
                    "source_path": result.payload.get("source_path", ""),
                },
                "score": round(1 - result.score, 4),  # Convert similarity to distance
            })

        return output
    except Exception as e:
        print(f"[QDRANT ERROR] Query failed: {e}")
        return []


def semantic_search(
    query: str,
    n_results: int = 5,
    subject: Optional[str] = None,
    unit: Optional[str] = None,
    doc_type: Optional[str] = None,
) -> List[Dict]:
    """Semantic search with optional filters"""
    filters = []
    if subject:
        filters.append({"subject": {"$eq": subject}})
    if unit:
        filters.append({"unit": {"$eq": unit}})
    if doc_type:
        filters.append({"doc_type": {"$eq": doc_type}})

    where = None
    if len(filters) == 1:
        where = filters[0]
    elif len(filters) > 1:
        where = {"$and": filters}

    results = query_chunks(query, n_results=n_results, where=where)

    # Reformat to match original semantic_search output
    output = []
    for result in results:
        output.append({
            "text": result["text"],
            "subject": result["metadata"].get("subject", ""),
            "unit": result["metadata"].get("unit", ""),
            "doc_type": result["metadata"].get("doc_type", ""),
            "filename": result["metadata"].get("filename", ""),
            "score": result["score"],
        })

    return output


def get_all_chunks(where: dict = None) -> List[Dict]:
    """Get all chunks (with optional filter)"""
    client = get_client()
    if not client:
        return []

    try:
        # Qdrant doesn't have a simple "get all" - we need to scroll through
        filter_condition = None
        if where:
            filter_condition = _build_filter(where)

        # Use scroll API to retrieve all points
        all_points = []
        offset = None
        while True:
            points, next_offset = client.scroll(
                collection_name=COLLECTION_NAME,
                limit=1000,
                query_filter=filter_condition,
                offset=offset,
            )
            all_points.extend(points)
            if next_offset is None or len(points) == 0:
                break
            offset = next_offset

        output = []
        for point in all_points:
            output.append({
                "text": point.payload.get("text", ""),
                "metadata": {
                    "subject": point.payload.get("subject", ""),
                    "unit": point.payload.get("unit", ""),
                    "doc_type": point.payload.get("doc_type", ""),
                    "filename": point.payload.get("filename", ""),
                    "source_path": point.payload.get("source_path", ""),
                },
            })

        return output
    except Exception as e:
        print(f"[QDRANT ERROR] Failed to get all chunks: {e}")
        return []


def get_collection_stats() -> Dict:
    """Get collection statistics"""
    client = get_client()
    if not client:
        return {"total_chunks": 0, "subjects": [], "doc_types": {}}

    try:
        collection_info = client.get_collection(COLLECTION_NAME)
        total_chunks = collection_info.points_count

        if total_chunks == 0:
            return {
                "total_chunks": 0,
                "subjects": [],
                "doc_types": {},
            }

        # Scroll through all points to compute stats
        subjects = set()
        doc_types = {}
        offset = None

        while True:
            points, next_offset = client.scroll(
                collection_name=COLLECTION_NAME,
                limit=1000,
                offset=offset,
            )
            for point in points:
                payload = point.payload
                if payload.get("subject"):
                    subjects.add(payload["subject"])
                dt = payload.get("doc_type", "unknown")
                doc_types[dt] = doc_types.get(dt, 0) + 1

            if next_offset is None or len(points) == 0:
                break
            offset = next_offset

        return {
            "total_chunks": total_chunks,
            "subjects": sorted(list(subjects)),
            "doc_types": doc_types,
        }
    except Exception as e:
        print(f"[QDRANT ERROR] Failed to get stats: {e}")
        return {"error": str(e)}


def delete_subject(subject: str) -> int:
    """Delete all chunks for a subject"""
    client = get_client()
    if not client:
        return 0

    try:
        filter_condition = Filter(
            must=[FieldCondition(key="subject", match=MatchValue(value=subject))]
        )

        # Delete points matching the filter
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=filter_condition,
        )

        # Return count - we can try to estimate by getting remaining points
        collection_info = client.get_collection(COLLECTION_NAME)
        return collection_info.points_count
    except Exception as e:
        print(f"[QDRANT ERROR] Failed to delete subject: {e}")
        return 0


def list_collections() -> List[str]:
    """List all collections"""
    client = get_client()
    if not client:
        return []

    try:
        collections = client.get_collections().collections
        return [c.name for c in collections]
    except Exception:
        return []


def delete_collection(name: str) -> bool:
    """Delete a collection"""
    client = get_client()
    if not client:
        return False

    try:
        client.delete_collection(name)
        return True
    except Exception as e:
        print(f"[QDRANT ERROR] Failed to delete collection: {e}")
        return False


def reset_collection() -> None:
    """Delete and recreate the collection"""
    client = get_client()
    if not client:
        return

    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass  # Collection might not exist

    _ensure_collection()


def _build_filter(where: dict) -> Optional[Filter]:
    """Convert ChromaDB-style where clause to Qdrant filter"""
    if not where:
        return None

    try:
        # Handle $and conditions
        if "$and" in where:
            conditions = []
            for sub_where in where["$and"]:
                for key, condition in sub_where.items():
                    if isinstance(condition, dict) and "$eq" in condition:
                        conditions.append(FieldCondition(key=key, match=MatchValue(value=condition["$eq"])))

            if conditions:
                return Filter(must=conditions)
            return None

        # Handle single condition: {"field": {"$eq": "value"}}
        for key, condition in where.items():
            if isinstance(condition, dict) and "$eq" in condition:
                return Filter(
                    must=[FieldCondition(key=key, match=MatchValue(value=condition["$eq"]))]
                )

        return None
    except Exception as e:
        print(f"[QDRANT ERROR] Failed to build filter: {e}")
        return None