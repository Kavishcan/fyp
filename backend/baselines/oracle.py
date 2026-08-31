"""Qrel-derived upper bound: maximum achievable source-selection reference.

Cheats by construction — it is a ceiling to measure other routers against, not
a routable system. Requires ground-truth relevance judgments (qrels), so it can
only be used on datasets that ship them (e.g. FeB4RAG).
"""
from __future__ import annotations

import time

from .base import RoutingResult, SourceProfile, SourceRouter


class OracleRouter(SourceRouter):
    def __init__(self, qrels: dict[str, list[str]]) -> None:
        """`qrels`: query_id -> relevant source_ids, best-first or unordered."""
        self._qrels = qrels
        self._known_sources: set[str] = set()

    def register_sources(self, profiles: list[SourceProfile]) -> None:
        self._known_sources = {p.source_id for p in profiles}

    def rank(self, query_embedding, top_k: int, query_id: str | None = None) -> RoutingResult:
        start = time.perf_counter()
        if query_id is None:
            raise ValueError("OracleRouter.rank requires query_id to consult qrels")
        relevant = [s for s in self._qrels.get(query_id, []) if s in self._known_sources]
        selected = relevant[:top_k] if top_k else relevant
        latency_ms = (time.perf_counter() - start) * 1000
        return RoutingResult(ranked_source_ids=selected, latency_ms=latency_ms)
