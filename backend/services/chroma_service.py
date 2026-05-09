"""
backend/services/chroma_service.py
"""
from dotenv import load_dotenv
load_dotenv()
import os
import uuid
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.utils import embedding_functions

CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_store")
COLLECTION_NAME = "vtu_study_companion"


def _get_embedding_fn():
    return embedding_functions.DefaultEmbeddingFunction()


_client: Optional[chromadb.PersistentClient] = None  # Changed from HttpClient
_collection = None


def get_client():
    global _client

    if _client is None:
        # Create directory if it doesn't exist
        Path(CHROMA_DIR).mkdir(parents=True, exist_ok=True)
        
        # Use local persistent storage instead of cloud
        _client = chromadb.PersistentClient(path=CHROMA_DIR)

    return _client


def get_or_create_collection():
    global _collection

    if _collection is None:
        client = get_client()

        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=_get_embedding_fn(),
            metadata={"hnsw:space": "cosine"},
        )

    return _collection


def add_chunks(
    collection_name: str,
    chunks: list[str],
    metadatas: list[dict] = None,
) -> int:

    collection = get_or_create_collection()

    if metadatas is None:
        metadatas = [{} for _ in chunks]

    ids = [uuid.uuid4().hex for _ in chunks]

    # Add in batches to avoid memory issues with large files
    batch_size = 500
    total_added = 0
    
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i+batch_size]
        batch_metadatas = metadatas[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]
        
        collection.add(
            ids=batch_ids,
            documents=batch_chunks,
            metadatas=batch_metadatas,
        )
        total_added += len(batch_chunks)

    return total_added


def semantic_search(
    query: str,
    n_results: int = 5,
    subject: Optional[str] = None,
    unit: Optional[str] = None,
    doc_type: Optional[str] = None,
) -> list:

    collection = get_or_create_collection()

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

    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

    except Exception as e:
        print(f"[CHROMA ERROR] {e}")
        return []

    output = []

    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        output.append(
            {
                "text": doc,
                "subject": meta.get("subject", ""),
                "unit": meta.get("unit", ""),
                "doc_type": meta.get("doc_type", ""),
                "filename": meta.get("filename", ""),
                "score": round(1 - dist, 4),
            }
        )

    return output


def query_chunks(
    query: str,
    n_results: int = 5,
    where: dict = None,
) -> list:

    collection = get_or_create_collection()

    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        output = []

        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            output.append(
                {
                    "text": doc,
                    "metadata": meta,
                    "score": round(1 - dist, 4),
                }
            )

        return output

    except Exception as e:
        print(f"[CHROMA ERROR] {e}")
        return []


def get_all_chunks(where: dict = None) -> list:

    collection = get_or_create_collection()

    try:
        results = collection.get(
            where=where,
            include=["documents", "metadatas"],
        )

        output = []

        for doc, meta in zip(
            results["documents"],
            results["metadatas"],
        ):
            output.append(
                {
                    "text": doc,
                    "metadata": meta,
                }
            )

        return output

    except Exception as e:
        print(f"[CHROMA ERROR] {e}")
        return []


def get_collection_stats() -> dict:

    try:
        collection = get_or_create_collection()
        count = collection.count()

        if count == 0:
            return {
                "total_chunks": 0,
                "subjects": [],
                "doc_types": {},
            }

        all_meta = collection.get(include=["metadatas"])["metadatas"]

        subjects = list(
            {
                m.get("subject", "")
                for m in all_meta
                if m.get("subject")
            }
        )

        doc_types = {}
        for m in all_meta:
            dt = m.get("doc_type", "unknown")
            doc_types[dt] = doc_types.get(dt, 0) + 1

        return {
            "total_chunks": count,
            "subjects": sorted(subjects),
            "doc_types": doc_types,
        }

    except Exception as e:
        return {"error": str(e)}


def delete_subject(subject: str) -> int:

    collection = get_or_create_collection()

    results = collection.get(where={"subject": {"$eq": subject}})
    ids = results["ids"]

    if ids:
        collection.delete(ids=ids)

    return len(ids)


def list_collections() -> list[str]:

    client = get_client()
    return [c.name for c in client.list_collections()]


def delete_collection(name: str) -> bool:

    try:
        client = get_client()
        client.delete_collection(name)
        return True
    except Exception:
        return False


def reset_collection() -> None:
    """Delete and recreate the collection - useful for fresh starts"""
    try:
        client = get_client()
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass  # Collection might not exist
    
    global _collection
    _collection = None
    get_or_create_collection()