"""Bounded trust update (docs/04-router-design.md section 8).

This is an independent implementation of the update rule described in the
reviewed literature (evidence relevance, profile consistency, cross-source
agreement, provenance validity, service reliability -> a bounded moving
average). It is NOT the upstream TASR code — see baselines/tasr_adapter.py for
that. Reproducing the real RQ03 interference result requires the actual
upstream implementation; this module is useful for prototyping the mechanism
and for the standalone claim that a decoy-aware exemption changes behaviour,
but a result reported against "TASR" must come from tasr_adapter.py.

An unmodified condition (decoy_aware=False) must exist and be run before any
decoy-aware change is measured against it (docs/04-router-design.md, and the
house rule in CLAUDE.md) — do not assume the exemption fix works before E1-E4.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TrustSignalWeights:
    evidence_relevance: float = 1.0
    profile_consistency: float = 1.0
    cross_source_agreement: float = 1.0
    provenance_validity: float = 1.0
    service_reliability: float = 1.0


@dataclass
class TrustSignalInputs:
    """Per-source observations for one query, each expected in [0, 1]."""

    evidence_relevance: float
    profile_consistency: float
    cross_source_agreement: float
    provenance_validity: float
    service_reliability: float


def compute_trust_signal(inputs: TrustSignalInputs, weights: TrustSignalWeights | None = None) -> float:
    weights = weights or TrustSignalWeights()
    total_weight = (
        weights.evidence_relevance
        + weights.profile_consistency
        + weights.cross_source_agreement
        + weights.provenance_validity
        + weights.service_reliability
    )
    weighted_sum = (
        weights.evidence_relevance * inputs.evidence_relevance
        + weights.profile_consistency * inputs.profile_consistency
        + weights.cross_source_agreement * inputs.cross_source_agreement
        + weights.provenance_validity * inputs.provenance_validity
        + weights.service_reliability * inputs.service_reliability
    )
    # Normalise so the signal stays in [0, 1] regardless of the weight scale,
    # which keeps it compatible with the [0, 1] trust range below.
    return weighted_sum / total_weight if total_weight else 0.0


class BoundedTrustUpdate:
    """Maintains per-source trust in [0, 1] with a slow exponential update.

    `decoy_aware=False` (default) is the unmodified baseline condition: every
    contacted source is updated identically, including sources that were
    decoys. `decoy_aware=True` exempts sources flagged as decoys for that
    query from the update. Both conditions must be run and compared, not just
    the decoy-aware one — the exemption itself may be observable and is the
    subject of experiment E4.
    """

    def __init__(self, alpha: float = 0.1, decoy_aware: bool = False) -> None:
        if not 0 < alpha <= 1:
            raise ValueError("alpha must be in (0, 1]")
        self.alpha = alpha
        self.decoy_aware = decoy_aware
        self._trust: dict[str, float] = {}

    def get(self, source_id: str, default: float = 0.5) -> float:
        return self._trust.get(source_id, default)

    def update(self, signals: dict[str, float], decoy_ids: frozenset[str] = frozenset()) -> None:
        for source_id, signal in signals.items():
            if self.decoy_aware and source_id in decoy_ids:
                continue
            current = self._trust.get(source_id, 0.5)
            updated = (1 - self.alpha) * current + self.alpha * signal
            self._trust[source_id] = min(1.0, max(0.0, updated))

    def snapshot(self) -> dict[str, float]:
        return dict(self._trust)
