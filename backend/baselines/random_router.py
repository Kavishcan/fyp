"""Random top-k control: weak selection baseline."""
from __future__ import annotations

import random
import time

from .base import RoutingResult, SourceProfile, SourceRouter


class RandomRouter(SourceRouter):
    def __init__(self, seed: int | None = None) -> None:
        self._source_ids: list[str] = []
        self._rng = random.Random(seed)

    def register_sources(self, profiles: list[SourceProfile]) -> None:
        self._source_ids = [p.source_id for p in profiles]

    def rank(self, query_embedding, top_k: int, query_id: str | None = None) -> RoutingResult:
        start = time.perf_counter()
        pool = list(self._source_ids)
        self._rng.shuffle(pool)
        selected = pool[:top_k] if top_k else pool
        latency_ms = (time.perf_counter() - start) * 1000
        return RoutingResult(ranked_source_ids=selected, latency_ms=latency_ms)
