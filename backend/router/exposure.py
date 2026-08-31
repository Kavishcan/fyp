"""Exposure cost and budget enforcement (docs/04-router-design.md section 5).

Privacy is not used as an undefined label here — exposure is a measured
combination of proxies. Every proxy, normalisation and weight must be reported
and included in sensitivity analysis; none of the defaults below are claimed
to be correct until measured.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExposureWeights:
    sensitive_token_fraction: float = 1.0
    query_specificity: float = 1.0
    irrelevance_probability: float = 1.0
    route_linkability: float = 1.0


@dataclass
class ExposureFactors:
    """Per-source proxies, each expected in [0, 1]."""

    sensitive_token_fraction_sent: float
    query_specificity: float
    probability_source_is_irrelevant: float
    route_linkability: float


def exposure_cost(factors: ExposureFactors, weights: ExposureWeights | None = None) -> float:
    weights = weights or ExposureWeights()
    return (
        weights.sensitive_token_fraction * factors.sensitive_token_fraction_sent
        + weights.query_specificity * factors.query_specificity
        + weights.irrelevance_probability * factors.probability_source_is_irrelevant
        + weights.route_linkability * factors.route_linkability
    )


def enforce_exposure_budget(
    dispatch_order: list[str],
    per_source_cost: dict[str, float],
    exposure_budget: float,
    *,
    protected: frozenset[str] = frozenset(),
) -> list[str]:
    """Truncate `dispatch_order` so cumulative exposure cost stays within budget.

    Sources in `protected` (the genuine, relevant selections) are always kept
    even if they alone exceed the budget — the budget constrains how many
    decoys are added, not whether genuine results are served. Decoys are
    dropped in dispatch order until the running total fits.
    """
    kept: list[str] = []
    running_cost = 0.0
    for source_id in dispatch_order:
        cost = per_source_cost.get(source_id, 0.0)
        if source_id in protected:
            kept.append(source_id)
            running_cost += cost
            continue
        if running_cost + cost <= exposure_budget:
            kept.append(source_id)
            running_cost += cost
    return kept
