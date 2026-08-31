"""Broadcast-to-all control: maximum coverage, maximum exposure, maximum cost."""
from __future__ import annotations

import time

from .base import RoutingResult, SourceProfile, SourceRouter


class BroadcastRouter(SourceRouter):
    def __init__(self) -> None:
        self._source_ids: list[str] = []

    def register_sources(self, profiles: list[SourceProfile]) -> None:
        self._source_ids = [p.source_id for p in profiles]

    def rank(self, query_embedding, top_k: int, query_id: str | None = None) -> RoutingResult:
        start = time.perf_counter()
        selected = list(self._source_ids[:top_k]) if top_k else list(self._source_ids)
        latency_ms = (time.perf_counter() - start) * 1000
        return RoutingResult(ranked_source_ids=selected, latency_ms=latency_ms)
