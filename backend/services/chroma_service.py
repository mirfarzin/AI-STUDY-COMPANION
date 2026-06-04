"""
backend/services/chroma_service.py

Compatibility shim — re-exports all functions from qdrant_service.py.
The original ChromaDB implementation has been fully migrated to Qdrant Cloud.
All function signatures are preserved so existing imports continue to work.
"""

from services.qdrant_service import (
    get_qdrant_client as get_client,
    get_or_create_collection,
    add_chunks,
    semantic_search,
    query_chunks,
    get_all_chunks,
    get_collection_stats,
    delete_subject,
    list_collections,
    delete_collection,
    COLLECTION_NAME,
)

def reset_collection():
    """Stub — collection reset not implemented for Qdrant shim."""
    return False

__all__ = [
    "get_client",
    "get_or_create_collection",
    "add_chunks",
    "semantic_search",
    "query_chunks",
    "get_all_chunks",
    "get_collection_stats",
    "delete_subject",
    "list_collections",
    "delete_collection",
    "reset_collection",
    "COLLECTION_NAME",
]