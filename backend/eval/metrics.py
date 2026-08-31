"""Routing and retrieval metrics.

Coarse recall and final recall are always reported separately
(docs/04-router-design.md section 6, CLAUDE.md) — if the correct source is
dropped before reranking, no later stage can recover it, and merging the two
numbers hides which stage failed.
"""
from __future__ import annotations

import math


def recall_at_k(retrieved: list[str], relevant: set, k: int | None = None) -> float:
    """Fraction of `relevant` present in `retrieved[:k]`. 1.0 if `relevant` is empty."""
    if not relevant:
        return 1.0
    window = retrieved[:k] if k is not None else retrieved
    hit = len(set(window) & relevant)
    return hit / len(relevant)


def coarse_recall_at_k(coarse_candidates: list[str], relevant: set, k: int | None = None) -> float:
    """Same computation as recall_at_k, named separately so call sites cannot
    accidentally conflate the coarse-stage and final-stage numbers.
    """
    return recall_at_k(coarse_candidates, relevant, k)


def precision_at_k(retrieved: list[str], relevant: set, k: int | None = None) -> float:
    window = retrieved[:k] if k is not None else retrieved
    if not window:
        return 0.0
    hit = len(set(window) & relevant)
    return hit / len(window)


def reciprocal_rank(retrieved: list[str], relevant: set) -> float:
    for rank, source_id in enumerate(retrieved, start=1):
        if source_id in relevant:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved: list[str], relevant: set, k: int | None = None) -> float:
    window = retrieved[:k] if k is not None else retrieved
    dcg = sum(1.0 / math.log2(i + 2) for i, s in enumerate(window) if s in relevant)
    ideal_hits = min(len(relevant), len(window)) if window else len(relevant)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
    return dcg / idcg if idcg > 0 else 0.0


def audit_cost(dispatched: list[str], relevant: set) -> int:
    """Number of contacted sources with no legitimate interest in the query —
    logged accesses under a data-sharing agreement that were not relevant.
    """
    return len([s for s in dispatched if s not in relevant])
