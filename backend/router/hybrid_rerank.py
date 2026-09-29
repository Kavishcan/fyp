"""Hybrid dense + BM25 rerank of passages already on the device.

Blind unlock (docs/47) and PSI (docs/36) leave the device holding the
question and every unlocked passage in plaintext; ranking them is a purely
local step, so a stronger ranker changes retrieval quality and nothing that
leaves the device. This one adds lexical evidence to the dense cosine:

    score = z(cosine(query, passage)) + weight · z(BM25(question, passage))

z = standardised within the pool. BM25 statistics (IDF, average length) are
computed from the POOL — the passages this question unlocked — because the
device never sees a node's whole corpus. k1 = 1.2, b = 0.75 (the usual
defaults). The default weight 0.5 was chosen on one half of the PMC-Patients
queries and reported on the other (docs/48); it is a tuned constant for that
data, not a universal setting.

No model, no download, no network. Not a learned reranker.
"""
from __future__ import annotations

import math
import re
from collections import Counter

import numpy as np

DEFAULT_WEIGHT = 0.5
K1, B = 1.2, 0.75
_TOKEN = re.compile(r"(?u)\b\w\w+\b")
# Common English function words; clinical content words are kept.
_STOP = frozenset("""
a about above after again against all also am an and any are as at be because been before being below between
both but by can could did do does doing down during each few for from further had has have having he her here
hers herself him himself his how however i if in into is it its itself just me more most my myself no nor not
now of off on once only or other our ours ourselves out over own same she should so some such than that the
their theirs them themselves then there these they this those through to too under until up very was we were
what when where which while who whom why will with would you your yours yourself yourselves may might must shall
upon within without via per among
""".split())


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP]


def bm25_pool(question: str, documents: list[str], tokens: list[list[str]] | None = None,
              counts: list[Counter] | None = None) -> np.ndarray:
    """BM25 of `question` against each document, statistics from the pool.
    `counts` (per-document term Counters) lets an index that is built once —
    a hospital's own collection — skip re-tokenising per question."""
    if counts is None:
        docs = tokens if tokens is not None else [tokenize(d) for d in documents]
        counts = [Counter(d) for d in docs]
    n = len(counts)
    if n == 0:
        return np.zeros(0)
    lengths = np.array([sum(c.values()) for c in counts], dtype=np.float64)
    avg = lengths.mean() or 1.0
    q_terms = set(tokenize(question))
    scores = np.zeros(n)
    for term in q_terms:
        df = sum(1 for c in counts if term in c)
        if df == 0:
            continue
        idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
        tf = np.array([c.get(term, 0) for c in counts], dtype=np.float64)
        scores += idf * tf * (K1 + 1) / (tf + K1 * (1 - B + B * lengths / avg))
    return scores


def _z(x: np.ndarray) -> np.ndarray:
    sd = x.std()
    return (x - x.mean()) / sd if sd > 1e-12 else np.zeros_like(x)


def hybrid_scores(question: str, query_vector: np.ndarray, documents: list[str], embeddings: np.ndarray,
                  weight: float = DEFAULT_WEIGHT, counts: list[Counter] | None = None) -> np.ndarray:
    q = np.asarray(query_vector, dtype=np.float64)
    q = q / (np.linalg.norm(q) or 1.0)
    e = np.asarray(embeddings, dtype=np.float64)
    dense = (e @ q) / np.maximum(np.linalg.norm(e, axis=1), 1e-12)
    if weight == 0 or len(documents) < 2:
        return dense
    return _z(dense) + weight * _z(bm25_pool(question, documents, counts=counts))


def hybrid_rerank(question: str, query_vector: np.ndarray, passages: list[dict], top_n: int,
                  weight: float = DEFAULT_WEIGHT) -> list[tuple[str, float]]:
    """`passages`: dicts with "document" and "embedding" (the unlocked pool).
    Returns the top_n (document, hybrid score), best first."""
    if not passages:
        return []
    docs = [p["document"] for p in passages]
    scores = hybrid_scores(question, query_vector, docs, np.asarray([p["embedding"] for p in passages]), weight)
    order = np.argsort(-scores)[:top_n]
    return [(docs[i], float(scores[i])) for i in order]
