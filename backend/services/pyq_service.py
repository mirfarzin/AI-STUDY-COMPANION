"""
pyq_service.py — PYQ (Previous Year Questions) Analysis

Algorithm:
1. Pull all chunks with doc_type="pyq" from Qdrant.
2. Extract question-like sentences using regex heuristics (?, VTU keywords).
3. Embed all extracted questions using fastembed (already installed for Qdrant).
4. Greedy-cluster similar questions (cosine sim >= threshold).
5. Count unique documents each cluster appears in → frequency.
6. Infer "year" from the document name using a 4-digit year regex.
7. Assign probability label: High (freq>=3), Medium (2), Low (1).
"""

import re
import numpy as np

from services.qdrant_service import get_all_chunks

# ---------------------------------------------------------------------------
# Model — loaded lazily on first call so startup isn't blocked
# Uses fastembed (already installed) to avoid adding torch/sentence-transformers
# ---------------------------------------------------------------------------
_model = None


def _get_model():
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        _model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _model


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# VTU-style action verbs that start exam questions
_VTU_VERBS = (
    "Define", "Explain", "Describe", "List", "Compare", "Differentiate",
    "Discuss", "Illustrate", "Derive", "Prove", "Find", "Calculate",
    "State", "Write", "Mention", "Evaluate", "Analyze", "Analyse",
    "What", "How", "Why", "When", "Where", "Which", "Enlist",
    "Sketch", "Show", "Obtain", "Determine",
)

_VTU_RE = re.compile(
    r"^(" + "|".join(_VTU_VERBS) + r")\b",
    re.IGNORECASE,
)

_YEAR_RE = re.compile(r"(20\d{2})")


def _extract_year(doc_id: str) -> str:
    """Pull a 4-digit year from the doc_id; fall back to the doc_id itself."""
    m = _YEAR_RE.search(doc_id)
    return m.group(1) if m else doc_id


def _extract_questions(chunk: str) -> list[str]:
    """
    Split a text chunk into sentences and keep only question-like ones.
    Criteria:
      - Ends with '?'  OR  starts with a VTU action verb
      - At least 6 words (filters noise/headers)
      - At most 60 words (filters run-on passages)
    """
    # Split on sentence boundaries
    sentences = re.split(r"(?<=[.?!])\s+", chunk)
    questions = []
    for s in sentences:
        s = s.strip()
        words = s.split()
        if len(words) < 6 or len(words) > 60:
            continue
        if s.endswith("?") or _VTU_RE.match(s):
            questions.append(s)
    return questions


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two 1-D numpy arrays."""
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _probability(freq: int) -> str:
    if freq >= 3:
        return "High"
    if freq == 2:
        return "Medium"
    return "Low"


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def analyze_pyqs(
    similarity_threshold: float = 0.78,
    max_results: int = 50,
) -> list[dict]:
    """
    Analyze all PYQ chunks in Qdrant for repeated questions.

    Returns a list of dicts, sorted by frequency (descending):
      {
        "question":    str,   # canonical (longest) form of the question
        "frequency":   int,   # number of unique documents it appears in
        "years":       list,  # years / doc names it appeared in
        "probability": str,   # "High" | "Medium" | "Low"
      }
    """
    # Get all chunks with doc_type="pyq" from Qdrant
    pyq_chunks = get_all_chunks(where={"doc_type": {"$eq": "pyq"}})
    if not pyq_chunks:
        return []

    # Step 1 — gather all question candidates
    candidates: list[dict] = []  # {text, doc_id, year}
    for chunk_data in pyq_chunks:
        meta = chunk_data.get("metadata", {})
        doc_id = meta.get("filename", "unknown")
        year = _extract_year(doc_id)
        for q in _extract_questions(chunk_data["text"]):
            candidates.append({"text": q, "doc_id": doc_id, "year": year})

    if not candidates:
        return []

    # Step 2 — embed all candidates using fastembed
    model = _get_model()
    texts = [c["text"] for c in candidates]
    embeddings = list(model.embed(texts))  # list of numpy arrays

    # Step 3 — greedy clustering
    n = len(candidates)
    assigned = [False] * n
    clusters: list[list[int]] = []

    for i in range(n):
        if assigned[i]:
            continue
        cluster = [i]
        assigned[i] = True
        for j in range(i + 1, n):
            if assigned[j]:
                continue
            sim = _cosine_sim(embeddings[i], embeddings[j])
            if sim >= similarity_threshold:
                cluster.append(j)
                assigned[j] = True
        clusters.append(cluster)

    # Step 4 — build result rows
    results: list[dict] = []
    for cluster in clusters:
        sources = [candidates[idx] for idx in cluster]

        # Canonical form = longest question text in the cluster
        canonical = max(sources, key=lambda x: len(x["text"]))["text"]

        # Unique documents this cluster appears in
        unique_docs = list(dict.fromkeys(s["doc_id"] for s in sources))
        freq = len(unique_docs)

        # Unique years (preserving first-seen order)
        years = list(dict.fromkeys(s["year"] for s in sources))

        results.append({
            "question": canonical,
            "frequency": freq,
            "years": years,
            "probability": _probability(freq),
        })

    # Sort: primary = frequency desc, secondary = question length desc (richer text first)
    results.sort(key=lambda x: (-x["frequency"], -len(x["question"])))
    return results[:max_results]
