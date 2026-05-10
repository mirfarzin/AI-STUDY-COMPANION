import os
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
import uuid

_client = None
_collection_name = "vtu_study_companion"

def get_qdrant_client():
    global _client
    if _client is None:
        url = os.getenv("QDRANT_URL")
        api_key = os.getenv("QDRANT_API_KEY")
        if url and api_key:
            _client = QdrantClient(url=url, api_key=api_key)
            print("✅ Qdrant client initialized")
        else:
            print("⚠️ Qdrant credentials missing - vector search disabled")
            _client = None
    return _client

def get_or_create_collection():
    """Get or create collection - maintains compatibility with ChromaDB code"""
    client = get_qdrant_client()
    if not client:
        return None
    
    try:
        # Check if collection exists
        collections = client.get_collections()
        if not any(c.name == _collection_name for c in collections.collections):
            # Create collection if it doesn't exist
            from qdrant_client.models import VectorParams, Distance
            client.create_collection(
                collection_name=_collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
            print(f"✅ Created collection: {_collection_name}")
        return client
    except Exception as e:
        print(f"⚠️ Qdrant collection error: {e}")
        return None

def add_chunks(chunks, metadatas):
    """Add chunks to Qdrant - maintains compatibility"""
    client = get_qdrant_client()
    if not client:
        print("⚠️ Cannot add chunks: Qdrant not configured")
        return 0
    
    from chromadb.utils import embedding_functions
    embedding_fn = embedding_functions.DefaultEmbeddingFunction()
    
    points = []
    for i, (chunk, meta) in enumerate(zip(chunks, metadatas)):
        embedding = embedding_fn([chunk])[0]
        points.append(PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={"text": chunk, **meta}
        ))
    
    client.upsert(collection_name=_collection_name, points=points)
    return len(points)

def semantic_search(query, n_results=5, subject=None, unit=None, doc_type=None):
    """Search for similar chunks"""
    client = get_qdrant_client()
    if not client:
        return []
    
    from chromadb.utils import embedding_functions
    embedding_fn = embedding_functions.DefaultEmbeddingFunction()
    query_embedding = embedding_fn([query])[0]
    
    # Build filter
    filter_condition = None
    if subject:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        filter_condition = Filter(
            must=[FieldCondition(key="subject", match=MatchValue(value=subject))]
        )
    
    results = client.search(
        collection_name=_collection_name,
        query_vector=query_embedding,
        limit=n_results,
        query_filter=filter_condition
    )
    
    output = []
    for result in results:
        output.append({
            "text": result.payload["text"],
            "subject": result.payload.get("subject", ""),
            "unit": result.payload.get("unit", ""),
            "doc_type": result.payload.get("doc_type", ""),
            "filename": result.payload.get("filename", ""),
            "score": result.score
        })
    
    return output