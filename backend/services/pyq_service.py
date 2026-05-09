"""
pyq_service.py — PYQ (Previous Year Questions) Analysis

Algorithm:
1. Pull all chunks from every ChromaDB collection (each = one uploaded PDF).
2. Extract question-like sentences using regex heuristics (?, VTU keywords).
3. Embed all extracted questions using the same all-MiniLM-L6-v2 model.
4. Greedy-cluster similar questions (cosine sim >= threshold).
5. Count unique documents each cluster appears in → frequency.
6. Infer "year" from the document name using a 4-digit year regex.
7. Assign probability label: High (freq≥3), Medium (2), Low (1).
"""

import re
from sentence_transformers import SentenceTransformer, util

from services.qdrant_service import list_collections, get_all_chunks

# ---------------------------------------------------------------------------
# Model — loaded lazily on first call so startup isn't blocked
# ---------------------------------------------------------------------------
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
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
    chunks_per_doc: int = 80,
    max_results: int = 50,
) -> list[dict]:
    """
    Analyze all uploaded PYQ PDFs for repeated questions.

    Returns a list of dicts, sorted by frequency (descending):
      {
        "question":    str,   # canonical (longest) form of the question
        "frequency":   int,   # number of unique documents it appears in
        "years":       list,  # years / doc names it appeared in
        "probability": str,   # "High" | "Medium" | "Low"
      }
    """
    collections = list_collections()
    if not collections:
        return []

    # Step 1 — gather all question candidates
    candidates: list[dict] = []  # {text, doc_id, year}
    for doc_id in collections:
        year = _extract_year(doc_id)
        chunks = get_all_chunks(doc_id, limit=chunks_per_doc)
        for chunk in chunks:
            for q in _extract_questions(chunk):
                candidates.append({"text": q, "doc_id": doc_id, "year": year})

    if not candidates:
        return []

    # Step 2 — embed all candidates
    model = _get_model()
    texts = [c["text"] for c in candidates]
    embeddings = model.encode(texts, convert_to_tensor=True, show_progress_bar=False)

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
            sim = float(util.cos_sim(embeddings[i], embeddings[j]))
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
