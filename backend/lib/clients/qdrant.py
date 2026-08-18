import os
import uuid
import hashlib
from typing import List, Dict, Optional, Any
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance, Filter, MatchValue, FieldCondition

# PUBLIC EXPORTS
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "vtu_study_companion")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

AUTHORITATIVE_FIRST_YEAR_SUBJECTS = [
    "Mathematics",
    "Physics",
    "Communication English",
    "Kannada Kali / Manasu",
    "A Scientific Approach to Health",
    "Principles of Programming Using C",
    "ESC",
    "PLC",
    "Chemistry",
    "Professional Writing Skills in English",
    "Constitution of India",
    "Design Thinking",
    "Computer-Aided Engineering Drawing",
    "ETC"
]

EXCLUDED_SUBJECTS = {
    "AI and ML",
    "Analysis and Design of Algorithms",
    "Computer Networks",
    "Data Science",
    "Database Management Systems",
    "Microcontrollers",
    "Operating Systems",
    "Software Engineering"
}

RAW_TO_CANONICAL_SUBJECT_MAP = {
    "CAED": "Computer-Aided Engineering Drawing",
    "Computer-Aided Engineering Drawing": "Computer-Aided Engineering Drawing",
    "Chemistry": "Chemistry",
    "Communication English": "Communication English",
    "Constitution of India": "Constitution of India",
    "Design Thinking": "Design Thinking",
    "ESC": "ESC",
    "ETC": "ETC",
    "Kannada Kali Manasu": "Kannada Kali / Manasu",
    "Kannada Kali / Manasu": "Kannada Kali / Manasu",
    "Mathematics ChemistryCycle": "Mathematics",
    "Mathematics PhysicsCycle": "Mathematics",
    "Mathematics": "Mathematics",
    "Physics": "Physics",
    "PLC": "PLC",
    "Principles of Programming C": "Principles of Programming Using C",
    "Principles of Programming Using C": "Principles of Programming Using C",
    "Professional Writing English": "Professional Writing Skills in English",
    "Professional Writing Skills in English": "Professional Writing Skills in English",
    "Scientific Approach to Health": "A Scientific Approach to Health",
    "A Scientific Approach to Health": "A Scientific Approach to Health"
}

CANONICAL_TO_RAW_SUBJECT_MAP = {
    "Mathematics": ["Mathematics", "Mathematics ChemistryCycle", "Mathematics PhysicsCycle"],
    "Physics": ["Physics"],
    "Communication English": ["Communication English"],
    "Kannada Kali / Manasu": ["Kannada Kali / Manasu", "Kannada Kali Manasu"],
    "A Scientific Approach to Health": ["A Scientific Approach to Health", "Scientific Approach to Health"],
    "Principles of Programming Using C": ["Principles of Programming Using C", "Principles of Programming C"],
    "ESC": ["ESC"],
    "PLC": ["PLC"],
    "Chemistry": ["Chemistry"],
    "Professional Writing Skills in English": ["Professional Writing Skills in English", "Professional Writing English"],
    "Constitution of India": ["Constitution of India"],
    "Design Thinking": ["Design Thinking"],
    "Computer-Aided Engineering Drawing": ["Computer-Aided Engineering Drawing", "CAED"],
    "ETC": ["ETC"]
}

def get_raw_subject_filter_values(subject: str) -> List[str]:
    if not subject:
        return []
    s = subject.strip()
    if s in CANONICAL_TO_RAW_SUBJECT_MAP:
        return CANONICAL_TO_RAW_SUBJECT_MAP[s]
    canonical = RAW_TO_CANONICAL_SUBJECT_MAP.get(s)
    if canonical and canonical in CANONICAL_TO_RAW_SUBJECT_MAP:
        return CANONICAL_TO_RAW_SUBJECT_MAP[canonical]
    return [s]

_client: Optional[QdrantClient] = None
_embedding_model = None


def _get_embedding_fn():
    global _embedding_model
    if _embedding_model is None:
        from fastembed import TextEmbedding
        _embedding_model = TextEmbedding(model_name=EMBEDDING_MODEL)
    return _embedding_model


def get_qdrant_client() -> Optional[QdrantClient]:
    """
    Returns a Qdrant client. Priority:
    1. Qdrant Cloud (QDRANT_URL + QDRANT_API_KEY)
    2. Local embedded Qdrant (persistent path ./qdrant_data)
    3. In-memory Qdrant (fallback, data lost on restart)
    """
    global _client
    if _client is not None:
        return _client

    url = os.getenv("QDRANT_URL", "").strip()
    key = os.getenv("QDRANT_API_KEY", "").strip()

    if url and key:
        try:
            candidate = QdrantClient(url=url, api_key=key, timeout=15, check_compatibility=False)
            # Verify the connection actually works by listing collections
            candidate.get_collections()
            _client = candidate
            print(f"[OK] Qdrant Cloud connected: {url}")
            return _client
        except Exception as e:
            print(f"[WARN] Qdrant Cloud failed ({e}), falling back to local embedded mode.")

    # Fallback: local embedded Qdrant with a persistent path
    data_path = os.getenv("QDRANT_DATA_PATH", "./qdrant_data")
    try:
        os.makedirs(data_path, exist_ok=True)
        _client = QdrantClient(path=data_path)
        print(f"[OK] Qdrant embedded mode: {data_path}")
        return _client
    except Exception as e:
        print(f"[WARN] Qdrant embedded failed ({e}), using in-memory mode.")

    # Last resort: in-memory (data lost on restart)
    _client = QdrantClient(":memory:")
    print("[WARN] Qdrant running in-memory — data will not persist across restarts.")
    return _client


def get_or_create_collection() -> Optional[QdrantClient]:
    client = get_qdrant_client()
    if not client:
        return None
    try:
        existing = [c.name for c in client.get_collections().collections]
        if COLLECTION_NAME not in existing:
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )
            print(f"[OK] Created Qdrant collection: {COLLECTION_NAME}")
        return client
    except Exception as e:
        print(f"[ERROR] Qdrant collection setup failed: {e}")
        return None


def _generate_deterministic_uuid(filename: str, chunk_index: int) -> str:
    hash_hex = hashlib.md5(f"{filename}_{chunk_index}".encode("utf-8")).hexdigest()
    return f"{hash_hex[:8]}-{hash_hex[8:12]}-{hash_hex[12:16]}-{hash_hex[16:20]}-{hash_hex[20:]}"


def add_chunks(chunks: List[str], metadatas: List[Dict]) -> int:
    client = get_or_create_collection()
    if not client:
        return 0
    embed_fn = _get_embedding_fn()
    points = []
    for t, m, emb in zip(chunks, metadatas, embed_fn.embed(chunks)):
        filename = m.get("filename", "unknown")
        chunk_idx = m.get("chunk_index", 0)
        point_id = _generate_deterministic_uuid(filename, chunk_idx)
        points.append(PointStruct(id=point_id, vector=list(emb), payload={"text": t, **m}))
    if points:
        client.upsert(collection_name=COLLECTION_NAME, points=points)
    return len(points)


def semantic_search(
    query: str,
    n_results: int = 5,
    subject: Optional[str] = None,
    unit: Optional[str] = None,
    doc_type: Optional[str] = None,
) -> List[Dict]:
    client = get_qdrant_client()
    if not client:
        return []
    try:
        embed_fn = _get_embedding_fn()
        q_emb = [float(x) for x in list(embed_fn.embed([query]))[0]]
        filters = []
        if subject:
            raw_subs = get_raw_subject_filter_values(subject)
            if len(raw_subs) == 1:
                filters.append(FieldCondition(key="subject", match=MatchValue(value=raw_subs[0])))
            elif len(raw_subs) > 1:
                from qdrant_client.models import MatchAny
                filters.append(FieldCondition(key="subject", match=MatchAny(any=raw_subs)))
        if unit:
            filters.append(FieldCondition(key="unit", match=MatchValue(value=unit)))
        if doc_type:
            filters.append(FieldCondition(key="doc_type", match=MatchValue(value=doc_type)))

        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=q_emb,
            query_filter=Filter(must=filters) if filters else None,
            limit=n_results,
            with_payload=True,
        )
        out = []
        for r in results.points:
            raw_subj = r.payload.get("subject", "")
            if raw_subj in EXCLUDED_SUBJECTS:
                continue
            canonical_subj = RAW_TO_CANONICAL_SUBJECT_MAP.get(raw_subj, raw_subj)
            out.append({
                "text": r.payload.get("text", ""),
                "subject": canonical_subj,
                "unit": r.payload.get("unit", ""),
                "doc_type": r.payload.get("doc_type", ""),
                "filename": r.payload.get("filename", ""),
                "score": r.score,
            })
        return out
    except Exception as e:
        print(f"[ERROR] Qdrant search failed: {e}")
        return []


def get_all_chunks(where: Optional[Dict] = None) -> List[Dict]:
    client = get_qdrant_client()
    if not client:
        return []
    try:
        filters = []
        if where and "subject" in where:
            subj_val = where["subject"].get("$eq") if isinstance(where["subject"], dict) else where["subject"]
            if subj_val:
                raw_subs = get_raw_subject_filter_values(subj_val)
                if len(raw_subs) == 1:
                    filters.append(FieldCondition(key="subject", match=MatchValue(value=raw_subs[0])))
                elif len(raw_subs) > 1:
                    from qdrant_client.models import MatchAny
                    filters.append(FieldCondition(key="subject", match=MatchAny(any=raw_subs)))

        out, offset = [], None
        while True:
            pts, offset = client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=Filter(must=filters) if filters else None,
                limit=1000,
                offset=offset,
                with_payload=True,
            )
            for p in pts:
                raw_subj = p.payload.get("subject", "")
                if raw_subj in EXCLUDED_SUBJECTS:
                    continue
                canonical_subj = RAW_TO_CANONICAL_SUBJECT_MAP.get(raw_subj, raw_subj)
                meta = {k: v for k, v in p.payload.items() if k != "text"}
                meta["subject"] = canonical_subj
                out.append({
                    "text": p.payload.get("text", ""),
                    "metadata": meta,
                })
            if not offset:
                break
        return out
    except Exception as e:
        print(f"[ERROR] Qdrant scroll failed: {e}")
        return []


def get_collection_stats() -> Dict:
    client = get_qdrant_client()
    if not client:
        return {"total_chunks": 0, "subjects": list(AUTHORITATIVE_FIRST_YEAR_SUBJECTS), "doc_types": {}}
    try:
        total = client.count(collection_name=COLLECTION_NAME).count
        return {"total_chunks": total, "subjects": list(AUTHORITATIVE_FIRST_YEAR_SUBJECTS), "doc_types": {}}
    except Exception as e:
        print(f"[ERROR] Qdrant stats failed: {e}")
        return {"total_chunks": 0, "subjects": list(AUTHORITATIVE_FIRST_YEAR_SUBJECTS), "doc_types": {}}


def delete_subject(subject: str) -> int:
    client = get_qdrant_client()
    if not client:
        return 0
    try:
        raw_subs = get_raw_subject_filter_values(subject)
        for s in raw_subs:
            client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=Filter(must=[FieldCondition(key="subject", match=MatchValue(value=s))]),
            )
        return 1
    except Exception:
        return 0


def query_chunks(q: str, n: int = 5, where: Optional[Dict] = None) -> List[Dict]:
    subject = where.get("subject", {}).get("$eq") if where else None
    return semantic_search(q, n, subject=subject)


def list_collections() -> List[str]:
    c = get_qdrant_client()
    return [x.name for x in c.get_collections().collections] if c else []


def delete_collection(name: str) -> bool:
    c = get_qdrant_client()
    return c.delete_collection(collection_name=name) if c else False

