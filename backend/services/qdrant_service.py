"""
Qdrant Cloud service - replacement for ChromaDB
Handles all vector database operations for the VTU Study Companion
"""
import os
from typing import Optional, List, Dict
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range
from dotenv import load_dotenv

load_dotenv()

# Initialize Qdrant client
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "vtu_study_companion"
VECTOR_SIZE = 384  # Size of the embedding vectors from DefaultEmbeddingFunction

_client: Optional[QdrantClient] = None


def get_client() -> Optional[QdrantClient]:
    """Get or create Qdrant client"""
    global _client
    
    if _client is None and QDRANT_URL and QDRANT_API_KEY:
        _client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        # Ensure collection exists
        _ensure_collection()
    
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
        except Exception as e:
            print(f"[QDRANT WARNING] Could not create collection: {e}")


def _get_embedding(text: str) -> List[float]:
    """Get embedding for text using DefaultEmbeddingFunction"""
    try:
        from chromadb.utils import embedding_functions
        embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        return embedding_fn([text])[0]
    except Exception as e:
        print(f"[QDRANT ERROR] Failed to get embedding: {e}")
        return [0.0] * VECTOR_SIZE


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
    
    points = []
    
    for chunk, meta in zip(chunks, metadatas):
        try:
            embedding = _get_embedding(chunk)
            
            point_id = str(uuid.uuid4().int % (2**63))  # Qdrant requires uint64 IDs
            
            points.append({
                "id": int(point_id),
                "vector": embedding,
                "payload": {
                    "text": chunk,
                    "subject": meta.get("subject", ""),
                    "unit": meta.get("unit", ""),
                    "doc_type": meta.get("doc_type", ""),
                    "filename": meta.get("filename", ""),
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
                "text": result.payload["text"],
                "metadata": {
                    "subject": result.payload.get("subject", ""),
                    "unit": result.payload.get("unit", ""),
                    "doc_type": result.payload.get("doc_type", ""),
                    "filename": result.payload.get("filename", ""),
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
    where = {}
    
    filters = []
    if subject:
        filters.append({"subject": {"$eq": subject}})
    if unit:
        filters.append({"unit": {"$eq": unit}})
    if doc_type:
        filters.append({"doc_type": {"$eq": doc_type}})
    
    if len(filters) == 1:
        where = filters[0]
    elif len(filters) > 1:
        where = {"$and": filters}
    
    results = query_chunks(query, n_results=n_results, where=where if where else None)
    
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
        points, _ = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=10000,  # Adjust based on your needs
            query_filter=filter_condition,
        )
        
        output = []
        for point in points:
            output.append({
                "text": point.payload["text"],
                "metadata": {
                    "subject": point.payload.get("subject", ""),
                    "unit": point.payload.get("unit", ""),
                    "doc_type": point.payload.get("doc_type", ""),
                    "filename": point.payload.get("filename", ""),
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
        
        # Get all points to compute stats
        all_points, _ = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=10000,
        )
        
        subjects = set()
        doc_types = {}
        
        for point in all_points:
            payload = point.payload
            if payload.get("subject"):
                subjects.add(payload["subject"])
            
            dt = payload.get("doc_type", "unknown")
            doc_types[dt] = doc_types.get(dt, 0) + 1
        
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
    """List all collections - for Qdrant Cloud, just return our collection name if it exists"""
    client = get_client()
    if not client:
        return []
    
    try:
        client.get_collection(COLLECTION_NAME)
        return [COLLECTION_NAME]
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
        # Handle single condition
        if "$eq" in str(where):
            # Extract the field and value from ChromaDB format
            for key, condition in where.items():
                if isinstance(condition, dict) and "$eq" in condition:
                    return Filter(
                        must=[FieldCondition(key=key, match=MatchValue(value=condition["$eq"]))]
                    )
        
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
    except Exception as e:
        print(f"[QDRANT ERROR] Failed to build filter: {e}")
        return None