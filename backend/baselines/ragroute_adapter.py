"""Adapter for the official RAGRoute implementation — the primary routing baseline.

RAGRoute (vendor/ragroute, MIT, cloned at commit 77c163f1) is NOT a simple
importable router class. Per its own README, it is a multi-process system: an
HTTP server + coordinator process, a separate routing process hosting the
router model, per-source retrieval processes, and an LLM engine via Ollama.
Reproducing it means running that system and talking to it over HTTP
(`ragroute/http_server.py`), not importing its internals — the "black-box via
API" fallback in docs/10-baseline-selection.md, not the "official runnable
implementation directly" tier, because "directly" here still means running
their full stack.

This adapter therefore stays a stub. Making it real requires, in order:
  1. `pip install -r vendor/ragroute/requirements.txt` (separate environment —
     it targets Python 3.8+ and has its own heavy deps; do not merge into this
     project's venv without checking for conflicts).
  2. Ollama installed and running (a real external service, not a Python dep).
  3. `python main.py` in vendor/ragroute to start the coordinator/HTTP server.
  4. This adapter becomes an HTTP client against that running server.
Each of those is a real resource commitment (installing Ollama, running a
second long-lived process) and should be a deliberate, visible step, not
something silently triggered by importing this module.

Setup:
    git clone https://github.com/sacs-epfl/ragroute <vendor_path>
    # then follow vendor_path/README.md Quickstart before wiring this adapter
"""
from __future__ import annotations

from .base import RoutingResult, SourceProfile, SourceRouter

UPSTREAM_REPO = "https://github.com/sacs-epfl/ragroute"
UPSTREAM_COMMIT = "77c163f14855e3b412891fc97339986f0a640d79"  # HEAD at clone time, 2026-04-09


class RAGRouteAdapter(SourceRouter):
    def __init__(self, vendor_path: str | None = None, http_base_url: str | None = None) -> None:
        self.vendor_path = vendor_path
        self.http_base_url = http_base_url
        self._not_ready = (
            "RAGRouteAdapter requires the RAGRoute HTTP server actually running "
            f"(see module docstring): {UPSTREAM_REPO} @ {UPSTREAM_COMMIT}. "
            "See docs/04-router-design.md section 2 and docs/10-baseline-selection.md."
        )

    def register_sources(self, profiles: list[SourceProfile]) -> None:
        raise NotImplementedError(self._not_ready)

    def rank(self, query_embedding, top_k: int, query_id: str | None = None) -> RoutingResult:
        raise NotImplementedError(self._not_ready)
