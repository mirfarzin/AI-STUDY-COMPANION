import os
from qdrant_client import QdrantClient

_client = None

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
    return _client

def search(query, limit=5):
    client = get_qdrant_client()
    if not client:
        return []
    # Add your search logic here
    return []