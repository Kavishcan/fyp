"""v2 privacy pipeline selection and trust (docs/30-privacy-pipeline-v2.md).

Opt-in `routing_mode="v2"`. Legacy (router/pipeline.py) and smart
(router/smart.py) are preserved unchanged as independent controls.

What v2 changes, and only this:

1. Routing is local. Relevance is scored in the coordinator against public
   profiles with the raw query embedding; nothing leaves the process here.
2. One positive-cost exposure budget covers EVERY contact — genuine and decoy
   alike. There is no genuine-source exemption (unlike router/exposure.py's
   legacy `protected` set) and no fallback broadcast. If the budget cannot fit
   the genuine set, fewer genuine sources are contacted.
3. Decoys are topic-stable (router/anonymity.py) so repeated same-topic
   queries dispatch the same cover set — the measured A2 mitigation.
4. Dispatch is a shared-routing-space vector, never raw text, with an
   identical payload (same vector, same top_n) to every contacted node, so a
   decoy request is byte-for-byte indistinguishable from a genuine one at the
   node. `sigma > 0` perturbs the ONE vector that leaves; routing itself is
   never perturbed.
5. Trust is coordinator-embedded evidence consistency (router/smart.py's
   EvidenceTrust) made decoy-aware: a decoy contact is expected to return
   off-topic passages and is not penalised for it (experiment E3). The
   exemption is itself observable — a contacted node whose trust never moves
   was a decoy — which is experiment E4 (eval/run_v2_interference.py). Both
   are measured, not assumed.

None of this is query secrecy or a privacy guarantee. A routing-space vector
can be inverted toward the query (attacks/a1_inversion.py); "privacy" here
means fewer recipients and an observer who cannot tell genuine from decoy,
plus a plaintext-free wire. Gaussian noise is empirical embedding
perturbation, not differential privacy.
"""
from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field
from math import fsum, isfinite

import numpy as np

from baselines.base import SourceProfile
from baselines.cosine_router import CosineRouter
from router.anonymity import topic_stable_sample
from router.perturb import perturb_embedding
from router.smart import EvidenceTrust


@dataclass(frozen=True)
class V2Config:
    exposure_budget: float = 5.0
    max_sources: int = 5      # m: genuine + decoys, upper bound on contacts
    genuine_k: int = 2        # how many top-ranked sources are meant to answer
    coarse_k: int = 15        # candidate pool decoys are drawn from
    aggregation: str = "max"  # CosineRouter aggregation over profile centroids
    minimum_trust: float = 0.0
    sigma: float = 0.0        # perturbation of the ONE dispatched vector

    def __post_init__(self):
        if not isfinite(self.exposure_budget) or self.exposure_budget < 0:
            raise ValueError("exposure_budget must be finite and nonnegative")
        for name in ("max_sources", "genuine_k", "coarse_k"):
            value = getattr(self, name)
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        if self.genuine_k > self.max_sources:
            raise ValueError("genuine_k cannot exceed max_sources")
        if not isfinite(self.minimum_trust) or not 0 <= self.minimum_trust <= 1:
            raise ValueError("minimum_trust must be finite and in [0, 1]")
        if not isfinite(self.sigma) or self.sigma < 0:
            raise ValueError("sigma must be finite and nonnegative")
        if self.aggregation not in {"max", "mean", "top_r_mean"}:
            raise ValueError("aggregation must be max, mean or top_r_mean")


@dataclass
class V2Decision:
    genuine_source_ids: list[str] = field(default_factory=list)
    decoy_source_ids: list[str] = field(default_factory=list)
    dispatched_source_ids: list[str] = field(default_factory=list)   # shuffled order, genuine+decoy mixed
    coarse_candidate_ids: list[str] = field(default_factory=list)
    excluded: dict[str, str] = field(default_factory=dict)
    steps: list[dict] = field(default_factory=list)
    exposure_spent: float = 0.0
    stop_reason: str = "no_candidates"
    config: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def dispatch_payload(vector: np.ndarray, top_n: int) -> dict:
    """The exact request every contacted node receives. Building it once and
    reusing it for every node is what makes genuine and decoy requests
    indistinguishable at the recipient (tested in tests/test_v2_router.py).
    """
    return {"vector": [float(x) for x in np.asarray(vector, dtype=np.float64)], "top_n": int(top_n)}


def select_dispatch(
    query_embedding: np.ndarray,
    profiles: list[SourceProfile],
    *,
    trust: dict[str, float],
    per_source_cost: dict[str, float],
    topic_key: str,
    config: V2Config | None = None,
    order_rng: random.Random | None = None,
) -> V2Decision:
    """Rank locally, take the genuine set within budget, pad with topic-stable
    decoys within the remaining budget, shuffle the dispatch order.

    `trust` and `per_source_cost` are coordinator-owned inputs; missing entries
    default to neutral 0.5 trust and unit cost. Every cost must be positive.
    """
    config = config or V2Config()
    decision = V2Decision(config=asdict(config))
    query = np.asarray(query_embedding, dtype=np.float64)
    if query.ndim != 1 or query.size == 0 or not np.isfinite(query).all():
        raise ValueError("query must be a finite nonempty vector")
    if not profiles or config.max_sources == 0:
        decision.stop_reason = "no_candidates" if not profiles else "max_sources_zero"
        return decision

    eligible: list[SourceProfile] = []
    for profile in profiles:
        cost = per_source_cost.get(profile.source_id, 1.0)
        if not isfinite(cost) or cost <= 0:
            raise ValueError(f"exposure cost for {profile.source_id!r} must be finite and positive")
        if trust.get(profile.source_id, 0.5) < config.minimum_trust:
            decision.excluded[profile.source_id] = "insufficient_trust"
            continue
        eligible.append(profile)
    if not eligible:
        decision.stop_reason = "no_eligible_sources"
        return decision

    router = CosineRouter(aggregation=config.aggregation)
    router.register_sources(eligible)
    ranking = router.rank(query, top_k=config.coarse_k)
    candidates = list(ranking.ranked_source_ids)
    decision.coarse_candidate_ids = candidates

    spent: list[float] = []

    def affordable(source_id: str) -> bool:
        return fsum([*spent, per_source_cost.get(source_id, 1.0)]) <= config.exposure_budget

    for source_id in candidates:
        if len(decision.genuine_source_ids) >= config.genuine_k:
            break
        cost = per_source_cost.get(source_id, 1.0)
        if not affordable(source_id):
            decision.excluded[source_id] = "exposure_budget"
            continue
        spent.append(cost)
        decision.genuine_source_ids.append(source_id)
        decision.steps.append({
            "source_id": source_id, "role": "genuine",
            "relevance": ranking.scores.get(source_id), "exposure_cost": cost,
            "cumulative_exposure": fsum(spent),
        })

    pool = [s for s in candidates if s not in decision.genuine_source_ids and s not in decision.excluded]
    wanted = max(0, config.max_sources - len(decision.genuine_source_ids))
    for source_id in topic_stable_sample(pool, len(pool), topic_key):
        if len(decision.decoy_source_ids) >= wanted:
            break
        cost = per_source_cost.get(source_id, 1.0)
        if not affordable(source_id):
            decision.excluded[source_id] = "exposure_budget"
            continue
        spent.append(cost)
        decision.decoy_source_ids.append(source_id)
        decision.steps.append({
            "source_id": source_id, "role": "decoy",
            "relevance": ranking.scores.get(source_id), "exposure_cost": cost,
            "cumulative_exposure": fsum(spent),
        })

    decision.exposure_spent = fsum(spent)
    dispatched = [*decision.genuine_source_ids, *decision.decoy_source_ids]
    # Order must not encode role; a fresh RNG keeps it from being a stable fingerprint.
    (order_rng or random.Random()).shuffle(dispatched)
    decision.dispatched_source_ids = dispatched

    # "candidates_exhausted" must mean there were genuinely too few sources —
    # if the budget turned any candidate away, the budget is the real reason.
    budget_blocked = any(reason == "exposure_budget" for reason in decision.excluded.values())
    if len(dispatched) >= config.max_sources:
        decision.stop_reason = "max_sources"
    elif budget_blocked:
        decision.stop_reason = "exposure_budget"
    elif not dispatched:
        decision.stop_reason = "no_candidates"
    else:
        decision.stop_reason = "candidates_exhausted"
    return decision


def dispatched_vector(query_embedding: np.ndarray, sigma: float, rng: np.random.Generator) -> np.ndarray:
    """The single vector that leaves the coordinator. Routing used the raw
    embedding; only this copy is perturbed (empirical noise, not DP).
    """
    return perturb_embedding(np.asarray(query_embedding, dtype=np.float64), sigma, rng)


class DecoyAwareEvidenceTrust(EvidenceTrust):
    """EvidenceTrust plus an OPT-IN decoy exemption that MEASUREMENT REJECTED.

    `is_decoy=True` skips the trust update, on the E1 reasoning that a decoy
    returning off-topic passages should not be penalised for it. Two measured
    results (eval/run_v2_interference.py, docs/30) say not to enable it:

    1. E4 — the exemption is a perfect side channel. An observer who can see
       trust values identified decoys at precision 1.00 and recall 1.00 with the
       exemption on, versus 0.00/0.00 with it off. In this app that observer is
       trivially available: GET /nodes publishes per-source trust.
    2. E1's premise does not hold for this mechanism. EvidenceTrust scores
       passage-to-PROFILE consistency, not query relevance, so a decoy returning
       its own on-profile passages is barely penalised anyway — decoy-heavy
       sources ended at mean trust 0.852 versus 0.855 for genuine-heavy.

    So the API path leaves it OFF and updates trust for every contact. The flag
    stays for the A/B in eval/run_v2_interference.py; it must not become the
    default without a new experiment that resolves E4. One run, one
    configuration, hashing encoder — not a general claim about trust exemptions.
    """

    def __init__(self) -> None:
        super().__init__()
        self.skipped: dict[str, int] = {}

    def observe(self, source_id: str, profile: SourceProfile, passage_embeddings: np.ndarray, *, is_decoy: bool = False) -> None:
        if is_decoy:
            self.skipped[source_id] = self.skipped.get(source_id, 0) + 1
            return
        super().observe(source_id, profile, passage_embeddings)

    def reset(self, source_id: str) -> None:
        super().reset(source_id)
        self.skipped.pop(source_id, None)
