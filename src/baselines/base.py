"""Common adapter contract every source router (baseline or reproduced) must satisfy.

See docs/04-router-design.md section 1. The privacy layer in src/router/ operates
on RoutingResult objects and never depends on a specific router's internals, so
swapping in a reproduced baseline (RAGRoute, TASR) requires only a new adapter
here, not changes downstream.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class SourceProfile:
    """What a source publishes about itself. Never contains raw documents.

    centroids: ndarray (c x d) — cluster centres over the source's local corpus,
        already perturbed by the source before publication (docs/03-architecture.md
        offline path). Held here as a numpy array at runtime; typed loosely to
        avoid a hard numpy import for callers that only pass metadata around.
    """

    source_id: str
    centroids: "object"
    trust_mean: float = 0.5
    trust_observations: int = 0
    document_count_bucket: str = "unknown"
    policy_labels: list = field(default_factory=list)
    expected_latency_ms: float = 0.0
    profile_version: int = 1
    profile_signature: bytes = b""


@dataclass
class RoutingResult:
    """What a router returns for one query.

    ranked_source_ids: best-first, from this router alone (before any privacy
        layer or decoy injection).
    scores: comparable score per source id, where the router provides one. Not
        required to be comparable across routers.
    latency_ms: wall-clock time for this router's rank() call.
    internal_metrics: optional, router-specific (e.g. coarse-candidate count).
    """

    ranked_source_ids: list
    scores: dict = field(default_factory=dict)
    latency_ms: float = 0.0
    internal_metrics: dict = field(default_factory=dict)


class SourceRouter(ABC):
    """Adapter contract. Implementations must not silently change the wrapped
    router's ranking logic — an adapter forwards to the reproduced baseline, it
    does not reinterpret its output.
    """

    @abstractmethod
    def register_sources(self, profiles: list[SourceProfile]) -> None:
        """Replace the router's known source set with `profiles`."""

    @abstractmethod
    def rank(self, query_embedding, top_k: int, query_id: str | None = None) -> RoutingResult:
        """Return up to `top_k` source ids ranked best-first for this query.

        `query_id` is optional and ignored by most routers; it exists so a
        router that needs external lookup by query identity (e.g. OracleRouter
        consulting qrels) satisfies the same contract as every other router.
        """
