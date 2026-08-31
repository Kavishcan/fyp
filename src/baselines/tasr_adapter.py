"""Adapter for Mu and Li's routing-hijacking repository: A3, HERouter, and
unmodified TASR.

Does NOT reimplement TASR — src/router/trust.py implements a bounded trust
update consistent with the formula described in the reviewed literature, which
is a useful standalone mechanism but is not a substitute for running the actual
TASR code. The RQ03 interference result requires the real implementation,
because the claim is about how *their* update rule behaves under decoys, not
how a reimplementation behaves.

Setup (not done by this file):
    git clone https://github.com/Junjie-Mu/routing-hijacking-fedrag <vendor_path>
    # verify it runs, record commit/environment per docs/10-baseline-selection.md
"""
from __future__ import annotations

from .base import RoutingResult, SourceProfile, SourceRouter

UPSTREAM_REPO = "https://github.com/Junjie-Mu/routing-hijacking-fedrag"


class TASRAdapter(SourceRouter):
    """Wraps the upstream unmodified-TASR routing/trust condition."""

    def __init__(self, vendor_path: str | None = None) -> None:
        self.vendor_path = vendor_path
        self._not_ready = (
            "TASRAdapter requires the upstream repository to be cloned and "
            f"verified first: {UPSTREAM_REPO}. "
            "See docs/10-baseline-selection.md for the reproduction checklist."
        )

    def register_sources(self, profiles: list[SourceProfile]) -> None:
        raise NotImplementedError(self._not_ready)

    def rank(self, query_embedding, top_k: int, query_id: str | None = None) -> RoutingResult:
        raise NotImplementedError(self._not_ready)

    def run_hijack_attack(self, *args, **kwargs):
        """A3: replicate the upstream routing-hijack attack setup."""
        raise NotImplementedError(self._not_ready)
