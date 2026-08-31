"""Composition of a baseline router with the proposed privacy/trust layer.

Implements the online path in docs/03-architecture.md: perturb -> baseline
rank -> exposure-constrained rerank -> anonymity set -> (caller fans out and
feeds results back into trust.BoundedTrustUpdate). This module is
orchestration only — it does not compute relevance, trust, or exposure numbers
itself. Per-candidate features are supplied by the caller via `RerankFeatures`
so the pipeline never fabricates a measurement it hasn't actually taken.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from baselines.base import SourceRouter
from router.anonymity import add_decoys
from router.exposure import ExposureFactors, ExposureWeights, exposure_cost
from router.perturb import perturb_embedding


@dataclass
class RerankWeights:
    relevance: float = 1.0
    trust: float = 1.0
    authorization: float = 1.0
    exposure: float = 1.0
    communication_cost: float = 1.0
    latency: float = 1.0
    hijack_risk: float = 1.0


@dataclass
class RerankFeatures:
    """Per-candidate inputs to the exposure-constrained score, all measured or
    estimated by the caller — never invented by this module.
    """

    relevance: float
    trust: float
    authorized: bool
    exposure_factors: ExposureFactors
    communication_cost: float
    expected_latency: float
    hijack_risk: float


def score_candidate(
    features: RerankFeatures,
    weights: RerankWeights,
    exposure_weights: ExposureWeights | None = None,
) -> float:
    """docs/04-router-design.md section 5 scoring formula."""
    return (
        weights.relevance * features.relevance
        + weights.trust * features.trust
        + weights.authorization * (1.0 if features.authorized else 0.0)
        - weights.exposure * exposure_cost(features.exposure_factors, exposure_weights)
        - weights.communication_cost * features.communication_cost
        - weights.latency * features.expected_latency
        - weights.hijack_risk * features.hijack_risk
    )


def select_with_constraints(
    candidates: dict[str, RerankFeatures],
    weights: RerankWeights,
    *,
    top_k: int,
    minimum_trust: float = 0.0,
    exposure_weights: ExposureWeights | None = None,
) -> list[str]:
    """Apply the hard constraints (docs section 5) then rank by score.

    Hard constraints: authorized, trust at or above `minimum_trust`. Fan-out
    and exposure-budget constraints are enforced separately in
    `exposure.enforce_exposure_budget`, after decoys are added, since they
    apply to the dispatched set rather than the genuine candidate set alone.
    """
    eligible = {
        source_id: f
        for source_id, f in candidates.items()
        if f.authorized and f.trust >= minimum_trust
    }
    scored = {
        source_id: score_candidate(f, weights, exposure_weights) for source_id, f in eligible.items()
    }
    ranked = sorted(scored, key=scored.get, reverse=True)
    return ranked[:top_k]


@dataclass
class PipelineResult:
    dispatched_source_ids: list[str]
    genuine_source_ids: list[str]
    decoy_source_ids: list[str] = field(init=False)
    coarse_candidate_ids: list = field(default_factory=list)
    baseline_latency_ms: float = 0.0

    def __post_init__(self) -> None:
        genuine = set(self.genuine_source_ids)
        self.decoy_source_ids = [s for s in self.dispatched_source_ids if s not in genuine]


class PrivacyAwarePipeline:
    """Wires a baseline SourceRouter to the perturbation, rerank and anonymity
    stages. Trust updates happen after retrieval returns, so they are the
    caller's responsibility (see router.trust.BoundedTrustUpdate) rather than
    part of this pipeline's single `route` call.
    """

    def __init__(self, baseline_router: SourceRouter, rerank_weights: RerankWeights | None = None) -> None:
        self.baseline_router = baseline_router
        self.rerank_weights = rerank_weights or RerankWeights()

    def route(
        self,
        query_embedding: np.ndarray,
        *,
        coarse_k: int,
        top_k: int,
        m: int,
        topic_key: str,
        feature_provider,
        sigma: float = 0.0,
        rng: np.random.Generator | None = None,
        exposure_weights: ExposureWeights | None = None,
        minimum_trust: float = 0.0,
        exposure_budget: float | None = None,
        per_source_exposure_cost: dict | None = None,
        query_id: str | None = None,
    ) -> PipelineResult:
        """feature_provider(candidate_ids) -> dict[str, RerankFeatures]."""
        rng = rng or np.random.default_rng()
        perturbed = perturb_embedding(query_embedding, sigma, rng)

        coarse = self.baseline_router.rank(perturbed, top_k=coarse_k, query_id=query_id)
        candidates = coarse.ranked_source_ids
        if not candidates:
            return PipelineResult(
                dispatched_source_ids=[], genuine_source_ids=[], baseline_latency_ms=coarse.latency_ms
            )

        features = feature_provider(candidates)
        genuine = select_with_constraints(
            features,
            self.rerank_weights,
            top_k=top_k,
            minimum_trust=minimum_trust,
            exposure_weights=exposure_weights,
        )

        dispatched = add_decoys(genuine, candidates, m, topic_key=topic_key)

        if exposure_budget is not None:
            per_source_cost = per_source_exposure_cost or {
                source_id: exposure_cost(features[source_id].exposure_factors, exposure_weights)
                for source_id in dispatched
                if source_id in features
            }
            dispatched = self._enforce_budget(dispatched, per_source_cost, exposure_budget, set(genuine))

        return PipelineResult(
            dispatched_source_ids=dispatched,
            genuine_source_ids=genuine,
            coarse_candidate_ids=candidates,
            baseline_latency_ms=coarse.latency_ms,
        )

    @staticmethod
    def _enforce_budget(dispatched, per_source_cost, exposure_budget, protected):
        from router.exposure import enforce_exposure_budget

        return enforce_exposure_budget(
            dispatched, per_source_cost, exposure_budget, protected=frozenset(protected)
        )
