import os
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
import uuid
from typing import List, Dict, Optional

_client = None
COLLECTION_NAME = "vtu_study_companion"

def get_qdrant_client():
    global _client
    if _client is None:
        url = os.getenv("QDRANT_URL")
        api_key = os.getenv("QDRANT_API_KEY")
        if url and api_key:
            _client = QdrantClient(url=url, api_key=api_key)
            print("✅ Qdrant connected")
        else:
            print("⚠️ Qdrant disabled")
            _client = None
    return _client

def get_or_create_collection():
    client = get_qdrant_client()
    if not client:
        return None
    try:
        from qdrant_client.models import VectorParams, Distance
        collections = client.get_collections()
        if not any(c.name == COLLECTION_NAME for c in collections.collections):
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
        return client
    except Exception as e:
        print(f"Error: {e}")
        return None

def add_chunks(chunks: List[str], metadatas: List[Dict]) -> int:
    client = get_qdrant_client()
    if not client:
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
    client.upsert(collection_name=COLLECTION_NAME, points=points)
    return len(points)

def semantic_search(query: str, n_results: int = 5, subject=None, unit=None, doc_type=None):
    client = get_qdrant_client()
    if not client:
        return []
    from chromadb.utils import embedding_functions
    embedding_fn = embedding_functions.DefaultEmbeddingFunction()
    query_embedding = embedding_fn([query])[0]
    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_embedding,
        limit=n_results
    )
    output = []
    for r in results:
        output.append({
            "text": r.payload.get("text", ""),
            "subject": r.payload.get("subject", ""),
            "unit": r.payload.get("unit", ""),
            "doc_type": r.payload.get("doc_type", ""),
            "filename": r.payload.get("filename", ""),
            "score": r.score
        })
    return output

def get_all_chunks(where: dict = None):
    client = get_qdrant_client()
    if not client:
        return []
    scroll_result = client.scroll(collection_name=COLLECTION_NAME, limit=10000)
    output = []
    for point in scroll_result[0]:
        payload = point.payload
        text = payload.pop("text", "")
        output.append({
            "text": text,
            "metadata": payload
        })
    return output

def get_collection_stats():
    client = get_qdrant_client()
    if not client:
        return {"total_chunks": 0, "subjects": [], "doc_types": {}}
    count = client.count(collection_name=COLLECTION_NAME).count
    return {"total_chunks": count, "subjects": [], "doc_types": {}}

def delete_subject(subject: str):
    client = get_qdrant_client()
    if not client:
        return 0
    scroll = client.scroll(collection_name=COLLECTION_NAME, limit=10000)
    ids_to_delete = []
    for point in scroll[0]:
        if point.payload.get("subject") == subject:
            ids_to_delete.append(point.id)
    if ids_to_delete:
        client.delete(collection_name=COLLECTION_NAME, points_selector=ids_to_delete)
    return len(ids_to_delete)

def query_chunks(query: str, n_results: int = 5, where: dict = None):
    return semantic_search(query, n_results)

def list_collections():
    return [COLLECTION_NAME]

def delete_collection(name: str):
    client = get_qdrant_client()
    if not client:
        return False
    try:
        client.delete_collection(collection_name=COLLECTION_NAME)
        return True
    except:
        return False