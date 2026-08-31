"""Transparent, training-free relevance control.

Convention: query and centroid vectors are L2-normalised and scored by inner
product, so larger scores are better (docs/04-router-design.md section 4). This
is a brute-force numpy implementation, not a FAISS index — it exists as a
transparent local control, not as the scaling path for 1000+ sources.
"""
from __future__ import annotations

import time

import numpy as np

from .base import RoutingResult, SourceProfile, SourceRouter

AGGREGATIONS = ("max", "mean", "top_r_mean")


def _normalise(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=-1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return vectors / norms


def aggregate_scores(centroid_scores: np.ndarray, aggregation: str, top_r: int = 3) -> float:
    """Collapse per-centroid scores for one source into a single relevance score.

    `aggregation` is an ablation condition (docs/04-router-design.md section 4)
    — max-over-centroid is a design hypothesis here, not an assumed default.
    """
    if aggregation == "max":
        return float(np.max(centroid_scores))
    if aggregation == "mean":
        return float(np.mean(centroid_scores))
    if aggregation == "top_r_mean":
        r = min(top_r, centroid_scores.size)
        return float(np.mean(np.sort(centroid_scores)[-r:]))
    raise ValueError(f"unknown aggregation {aggregation!r}, expected one of {AGGREGATIONS}")


class CosineRouter(SourceRouter):
    def __init__(self, aggregation: str = "max", top_r: int = 3) -> None:
        if aggregation not in AGGREGATIONS:
            raise ValueError(f"aggregation must be one of {AGGREGATIONS}")
        self.aggregation = aggregation
        self.top_r = top_r
        self._source_ids: list[str] = []
        self._centroids: list[np.ndarray] = []

    def register_sources(self, profiles: list[SourceProfile]) -> None:
        self._source_ids = [p.source_id for p in profiles]
        self._centroids = [_normalise(np.asarray(p.centroids, dtype=np.float64)) for p in profiles]

    def rank(self, query_embedding, top_k: int, query_id: str | None = None) -> RoutingResult:
        start = time.perf_counter()
        q = _normalise(np.asarray(query_embedding, dtype=np.float64).reshape(1, -1))
        scores: dict[str, float] = {}
        for source_id, centroids in zip(self._source_ids, self._centroids):
            centroid_scores = centroids @ q[0]
            scores[source_id] = aggregate_scores(centroid_scores, self.aggregation, self.top_r)
        ranked = sorted(scores, key=scores.get, reverse=True)
        selected = ranked[:top_k] if top_k else ranked
        latency_ms = (time.perf_counter() - start) * 1000
        return RoutingResult(
            ranked_source_ids=selected,
            scores={s: scores[s] for s in selected},
            latency_ms=latency_ms,
            internal_metrics={"aggregation": self.aggregation},
        )
