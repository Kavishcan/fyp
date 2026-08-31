"""Adapter for the official RAGRoute implementation — the primary routing baseline.

This adapter does NOT reimplement RAGRoute. It exists to wrap the upstream
repository once it is cloned and verified to run, per the baseline acceptance
gate in docs/04-router-design.md section 2. Until that repository is present,
every method raises NotImplementedError rather than falling back to a
substitute — reporting a RAGRoute result without having run RAGRoute would
violate the project's baseline comparability rule (docs/05-experiments.md).

Setup (not done by this file):
    git clone https://github.com/sacs-epfl/ragroute <vendor_path>
    # verify the acceptance gate in docs/04-router-design.md section 2, then
    # record commit, environment and licence per docs/10-baseline-selection.md
    # before wiring this adapter to the real package.
"""
from __future__ import annotations

from .base import RoutingResult, SourceProfile, SourceRouter

UPSTREAM_REPO = "https://github.com/sacs-epfl/ragroute"


class RAGRouteAdapter(SourceRouter):
    def __init__(self, vendor_path: str | None = None) -> None:
        self.vendor_path = vendor_path
        self._not_ready = (
            "RAGRouteAdapter requires the upstream repository to be cloned and "
            f"verified against the acceptance gate first: {UPSTREAM_REPO}. "
            "See docs/04-router-design.md section 2 and docs/10-baseline-selection.md."
        )

    def register_sources(self, profiles: list[SourceProfile]) -> None:
        raise NotImplementedError(self._not_ready)

    def rank(self, query_embedding, top_k: int, query_id: str | None = None) -> RoutingResult:
        raise NotImplementedError(self._not_ready)
