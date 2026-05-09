"""
Qdrant Cloud service - replacement for ChromaDB when deployed
"""
import os
from typing import Optional, List, Dict
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Initialize Qdrant client only if cloud credentials exist
def get_qdrant_client():
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")
    
    if url and api_key:
        return QdrantClient(url=url, api_key=api_key)
    return None

_client = get_qdrant_client()
COLLECTION_NAME = "vtu_study_companion"

def add_chunks_qdrant(chunks: List[str], metadatas: List[Dict]) -> int:
    """Add chunks to Qdrant Cloud"""
    if not _client:
        return 0
    
    from chromadb.utils import embedding_functions
    embedding_fn = embedding_functions.DefaultEmbeddingFunction()
    
    points = []
    for idx, (chunk, meta) in enumerate(zip(chunks, metadatas)):
        embedding = embedding_fn([chunk])[0]
        points.append({
            "id": str(uuid.uuid4()),
            "vector": embedding,
            "payload": {
                "text": chunk,
                "subject": meta.get("subject", ""),
                "unit": meta.get("unit", ""),
                "doc_type": meta.get("doc_type", ""),
                "filename": meta.get("filename", ""),
            }
        })
    
    _client.upsert(collection_name=COLLECTION_NAME, points=points)
    return len(points)

def query_qdrant(query: str, n_results: int = 5, subject: Optional[str] = None) -> List[Dict]:
    """Search in Qdrant Cloud"""
    if not _client:
        return []
    
    from chromadb.utils import embedding_functions
    embedding_fn = embedding_functions.DefaultEmbeddingFunction()
    query_embedding = embedding_fn([query])[0]
    
    # Build filter
    filter_condition = None
    if subject:
        filter_condition = Filter(
            must=[FieldCondition(key="subject", match=MatchValue(value=subject))]
        )
    
    results = _client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_embedding,
        limit=n_results,
        query_filter=filter_condition,
    )
    
    output = []
    for result in results:
        output.append({
            "text": result.payload["text"],
            "subject": result.payload.get("subject", ""),
            "unit": result.payload.get("unit", ""),
            "doc_type": result.payload.get("doc_type", ""),
            "filename": result.payload.get("filename", ""),
            "score": result.score,
        })
    
    return output