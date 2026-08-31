"""Adapter for Mu and Li's routing-hijacking repository: A3, HERouter, and
unmodified TASR.

Wraps the actual upstream `TrustAwareRouter` class
(vendor/routing-hijacking-fedrag/fedrag/rag/trust_defense.py), loaded directly
via importlib rather than `import fedrag`, because that package's `__init__.py`
eagerly imports `retriever.py`, which requires `datasets`/`sentence-transformers`/
`torch` — none of which are needed for the trust-defense logic itself. This
keeps the adapter usable without installing the upstream's full dependency set,
while still running their real code, not a reimplementation.

src/router/trust.py is a SEPARATE, independent reimplementation of the update
rule described in the paper — useful for prototyping, but a reported RQ03
result must come from THIS adapter, per the reproduction rule in CLAUDE.md.

Upstream: https://github.com/Junjie-Mu/routing-hijacking-fedrag (Apache-2.0)
"""
from __future__ import annotations

import importlib.util
import time
from pathlib import Path
from typing import Dict, List

import numpy as np

from .base import RoutingResult, SourceProfile, SourceRouter

UPSTREAM_REPO = "https://github.com/Junjie-Mu/routing-hijacking-fedrag"
_DEFAULT_VENDOR_PATH = Path(__file__).resolve().parent.parent / "vendor" / "routing-hijacking-fedrag"
_MODULE_RELATIVE_PATH = "fedrag/rag/trust_defense.py"


def _load_trust_defense_module(vendor_path: Path):
    module_path = vendor_path / _MODULE_RELATIVE_PATH
    if not module_path.exists():
        raise FileNotFoundError(
            f"upstream module not found at {module_path}. Clone it first:\n"
            f"    git clone {UPSTREAM_REPO} {vendor_path}"
        )
    spec = importlib.util.spec_from_file_location("_upstream_tasr_trust_defense", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


class TASRAdapter(SourceRouter):
    """Wraps the upstream unmodified-TASR routing/trust condition.

    Client ids in the upstream code are integers; SourceProfile ids are
    strings, so this adapter maintains the id<->source_id mapping.

    `doc_embeddings` is the evidence pool TASR uses to simulate what a client
    would return for feedback scoring. Supplying it is an evaluation-harness
    concern (the evaluator has access to it because this runs inside our own
    research simulation, not because it crosses a real trust boundary) — see
    docs/03-architecture.md on what actually leaves a node in a real
    deployment. Pass real evidence via `register_sources(..., doc_embeddings=)`
    when available; falls back to the profile's own centroids otherwise, which
    is weaker feedback signal and should be noted in any reported result.
    """

    def __init__(self, vendor_path: str | Path | None = None, **tasr_kwargs) -> None:
        self.vendor_path = Path(vendor_path) if vendor_path else _DEFAULT_VENDOR_PATH
        module = _load_trust_defense_module(self.vendor_path)
        self._router = module.TrustAwareRouter(**tasr_kwargs)
        self._id_to_source: Dict[int, str] = {}
        self._source_to_id: Dict[str, int] = {}
        self._next_id = 0

    def register_sources(
        self,
        profiles: List[SourceProfile],
        doc_embeddings: Dict[str, np.ndarray] | None = None,
    ) -> None:
        doc_embeddings = doc_embeddings or {}
        for profile in profiles:
            if profile.source_id not in self._source_to_id:
                self._source_to_id[profile.source_id] = self._next_id
                self._id_to_source[self._next_id] = profile.source_id
                self._next_id += 1
            client_id = self._source_to_id[profile.source_id]

            centroids = np.asarray(profile.centroids, dtype=np.float64)
            mean_centroid = centroids.mean(axis=0)
            evidence = doc_embeddings.get(profile.source_id)
            if evidence is None:
                # Weak fallback: use the published centroids as their own
                # evidence pool. Real evaluation should supply actual sampled
                # document embeddings for a meaningful consistency signal.
                evidence = centroids

            self._router.register_client(
                client_id,
                centroid=mean_centroid,
                doc_embeddings=np.asarray(evidence, dtype=np.float64),
                profile_centroids=centroids,
            )

    def rank(self, query_embedding, top_k: int, query_id: str | None = None) -> RoutingResult:
        start = time.perf_counter()
        selected_ids, raw_scores = self._router.route(np.asarray(query_embedding, dtype=np.float64), top_k=top_k)
        latency_ms = (time.perf_counter() - start) * 1000
        selected_sources = [self._id_to_source[i] for i in selected_ids]
        scores = {self._id_to_source[i]: s for i, s in raw_scores.items() if i in self._id_to_source}
        return RoutingResult(ranked_source_ids=selected_sources, scores=scores, latency_ms=latency_ms)

    def update_trust(self, query_embedding, selected_source_ids: List[str], returned_docs=None) -> None:
        """Feed back retrieval evidence for the sources selected on the last
        `rank()` call, per the upstream trust-update contract.
        """
        selected_ids = [self._source_to_id[s] for s in selected_source_ids if s in self._source_to_id]
        upstream_returned_docs = None
        if returned_docs is not None:
            upstream_returned_docs = {
                self._source_to_id[s]: np.asarray(d, dtype=np.float64)
                for s, d in returned_docs.items()
                if s in self._source_to_id
            }
        self._router.update_trust(
            np.asarray(query_embedding, dtype=np.float64), selected_ids, upstream_returned_docs
        )

    def trust_summary(self, malicious_source_ids: List[str] | None = None) -> dict:
        malicious_ids = [self._source_to_id[s] for s in (malicious_source_ids or []) if s in self._source_to_id]
        return self._router.get_trust_summary(malicious_ids)
