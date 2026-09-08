"""Training-free greedy source selection with an explicit dispatch budget.

This is a proposed heuristic, not a reproduced baseline or a privacy proof.
Costs are coordinator-supplied exposure units; unit costs count recipients.
Source profiles and queries must use the same embedding space.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import fsum, isfinite, sqrt
from time import perf_counter

import numpy as np

from baselines.base import SourceProfile


@dataclass(frozen=True)
class SourceEvidence:
    # These inputs belong to the coordinator, not the source's self-report.
    trust: float = 0.5
    observations: int = 0
    authorized: bool = False
    exposure_cost: float = 1.0

    def __post_init__(self):
        if not isfinite(self.trust) or not 0 <= self.trust <= 1:
            raise ValueError("trust must be finite and in [0, 1]")
        if not isinstance(self.observations, int) or self.observations < 0:
            raise ValueError("observations must be a nonnegative integer")
        if not isfinite(self.exposure_cost) or self.exposure_cost < 1e-12:
            raise ValueError("exposure_cost must be finite and at least 1e-12")


@dataclass(frozen=True)
class SmartConfig:
    exposure_budget: float = 3.0
    max_sources: int = 5
    minimum_gain: float = 0.05
    minimum_trust: float = 0.0
    uncertainty_penalty: float = 0.1
    redundancy_weight: float = 1.0
    aggregation: str = "mean"

    def __post_init__(self):
        if not isfinite(self.exposure_budget) or self.exposure_budget < 0:
            raise ValueError("exposure_budget must be finite and nonnegative")
        if not isinstance(self.max_sources, int) or self.max_sources < 0:
            raise ValueError("max_sources must be a nonnegative integer")
        for name in ("minimum_gain", "minimum_trust", "uncertainty_penalty", "redundancy_weight"):
            value = getattr(self, name)
            if not isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be finite and in [0, 1]")
        if self.aggregation not in {"mean", "max"}:
            raise ValueError("aggregation must be mean or max")


@dataclass
class SmartDecision:
    selected_source_ids: list[str] = field(default_factory=list)
    candidate_source_ids: list[str] = field(default_factory=list)
    steps: list[dict] = field(default_factory=list)
    excluded: dict[str, str] = field(default_factory=dict)
    exposure_spent: float = 0.0
    stop_reason: str = "no_eligible_sources"
    latency_ms: float = 0.0
    config: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _unit_rows(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    if not np.isfinite(norms).all():
        raise ValueError("embedding norms must be finite")
    return np.divide(vectors, norms, out=np.zeros_like(vectors), where=norms != 0)


class SmartRouter:
    """Greedily choose the affordable source with greatest gain per cost.

    gain = relevance * effective_trust * (1 - redundancy_weight * redundancy)
    effective_trust = max(0, trust - uncertainty_penalty / sqrt(n + 1))
    Redundancy is the maximum positive centroid cosine to any selected source.
    It is only a profile-overlap proxy, not measured answer/evidence coverage.
    """

    def route(
        self,
        query_embedding: np.ndarray,
        profiles: list[SourceProfile],
        evidence: dict[str, SourceEvidence],
        config: SmartConfig | None = None,
    ) -> SmartDecision:
        start = perf_counter()
        config = config or SmartConfig()
        decision = SmartDecision(config=asdict(config))
        query = np.asarray(query_embedding, dtype=np.float64)
        if query.ndim != 1 or query.size == 0 or not np.isfinite(query).all():
            raise ValueError("query must be a finite nonempty vector")
        query = _unit_rows(query[None, :])[0]
        if len({p.source_id for p in profiles}) != len(profiles):
            raise ValueError("source IDs must be unique")

        remaining = {}
        for profile in sorted(profiles, key=lambda p: p.source_id):
            sid = profile.source_id
            entry = evidence.get(sid)
            if entry is None or not entry.authorized:
                decision.excluded[sid] = "unauthorized_or_missing_evidence"
                continue
            effective_trust = max(0.0, entry.trust - config.uncertainty_penalty / sqrt(entry.observations + 1))
            if effective_trust < config.minimum_trust:
                decision.excluded[sid] = "insufficient_trust"
                continue
            centroids = np.asarray(profile.centroids, dtype=np.float64)
            if (centroids.ndim != 2 or centroids.shape[0] == 0
                    or centroids.shape[1] != query.size or not np.isfinite(centroids).all()):
                decision.excluded[sid] = "invalid_profile"
                continue
            centroids = _unit_rows(centroids)
            scores = np.clip(centroids @ query, 0.0, 1.0)
            relevance = float(np.mean(scores) if config.aggregation == "mean" else np.max(scores))
            remaining[sid] = (centroids, relevance, effective_trust, entry)

        decision.candidate_source_ids = list(remaining)
        redundancy = {sid: 0.0 for sid in remaining}
        while remaining and len(decision.selected_source_ids) < config.max_sources:
            ranked = []
            for sid, (_, relevance, trust, entry) in remaining.items():
                gain = relevance * trust * (1 - config.redundancy_weight * redundancy[sid])
                if gain > config.minimum_gain:
                    ranked.append((sid, gain, gain / entry.exposure_cost))
            if not ranked:
                decision.stop_reason = "insufficient_gain"
                break
            spent_costs = [step["exposure_cost"] for step in decision.steps]
            affordable = [item for item in ranked if
                          remaining[item[0]][3].exposure_cost <= config.exposure_budget - decision.exposure_spent and
                          fsum([*spent_costs, remaining[item[0]][3].exposure_cost]) <= config.exposure_budget]
            if not affordable:
                decision.stop_reason = "exposure_budget"
                break
            sid, gain, ratio = min(affordable, key=lambda item: (-item[2], -item[1], item[0]))
            centroids, relevance, trust, entry = remaining.pop(sid)
            decision.selected_source_ids.append(sid)
            decision.exposure_spent = fsum([*spent_costs, entry.exposure_cost])
            decision.steps.append({
                "source_id": sid, "relevance": relevance, "effective_trust": trust,
                "redundancy": redundancy[sid], "marginal_gain": gain,
                "gain_per_cost": ratio, "exposure_cost": entry.exposure_cost,
                "cumulative_exposure": decision.exposure_spent,
            })
            for other, (other_centroids, _, _, _) in remaining.items():
                overlap = float(np.clip(np.max(other_centroids @ centroids.T), 0.0, 1.0))
                redundancy[other] = max(redundancy[other], overlap)
        else:
            if len(decision.selected_source_ids) >= config.max_sources:
                decision.stop_reason = "max_sources"
            elif decision.selected_source_ids:
                decision.stop_reason = "candidates_exhausted"
        decision.latency_ms = (perf_counter() - start) * 1000
        return decision


class EvidenceTrust:
    """Coordinator-observed profile/evidence consistency, not verified honesty.

    Uses passage embeddings from the coordinator's own encoder, ignoring
    retrieval scores and trust values advertised by remote sources. An attacker
    can still return matching bait passages; this is not a complete defence.
    """

    def __init__(self) -> None:
        self.values: dict[str, tuple[float, int]] = {}

    def get(self, source_id: str) -> tuple[float, int]:
        return self.values.get(source_id, (0.5, 0))

    def reset(self, source_id: str) -> None:
        self.values.pop(source_id, None)

    def observe(self, source_id: str, profile: SourceProfile, passage_embeddings: np.ndarray) -> None:
        previous, count = self.get(source_id)
        passages = np.asarray(passage_embeddings, dtype=np.float64)
        centroids = np.asarray(profile.centroids, dtype=np.float64)
        signal = 0.0
        if passages.size:
            if (passages.ndim != 2 or centroids.ndim != 2 or not len(centroids)
                    or passages.shape[1] != centroids.shape[1]
                    or not np.isfinite(passages).all() or not np.isfinite(centroids).all()):
                raise ValueError("passage and profile embeddings must be finite and compatible")
            similarities = _unit_rows(passages) @ _unit_rows(centroids).T
            signal = float(np.mean(np.clip(np.max(similarities, axis=1), 0.0, 1.0)))
        # A neutral two-observation prior and one coordinator observation/query.
        self.values[source_id] = ((previous * (count + 2) + signal) / (count + 3), count + 1)
