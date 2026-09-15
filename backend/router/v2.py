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
    # docs/39–40: "topic_stable" pads the genuine set with per-topic decoys
    # (hides which contact is genuine, does not hide the topic); "cells"
    # dispatches the whole fixed cell of each genuine source (hides both, at
    # one fewer genuine contact). Cells are supplied by the caller.
    decoy_policy: str = "topic_stable"
    # docs/32 found the trust GATE inert (≤0.5) or deadlocking (>0.5). This is
    # the ranking-term alternative it named: candidates in the coarse pool are
    # re-ordered by relevance + trust_weight * (trust - 0.5). 0 = off, and
    # every earlier result is byte-identical at 0. Adopted only if the docs/32
    # ablation, re-run with it, says so (docs/42).
    trust_weight: float = 0.0

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
        if self.decoy_policy not in {"topic_stable", "cells"}:
            raise ValueError("decoy_policy must be topic_stable or cells")
        if not isfinite(self.trust_weight) or self.trust_weight < 0:
            raise ValueError("trust_weight must be finite and nonnegative")


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
    cells: list[list[str]] | None = None,
) -> V2Decision:
    """Rank locally, take the genuine set within budget, pad with topic-stable
    decoys within the remaining budget, shuffle the dispatch order.

    `trust` and `per_source_cost` are coordinator-owned inputs; missing entries
    default to neutral 0.5 trust and unit cost. Every cost must be positive.

    With `config.decoy_policy == "cells"`, `cells` (router/anonymity.build_cells)
    is required: for each genuine source in rank order, its whole cell is
    dispatched if the cell fits the remaining budget and `max_sources`;
    otherwise that genuine source is skipped rather than contacted outside
    its cell. Cell mates are recorded as decoys.
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
    if config.trust_weight > 0:
        # Demote, never exclude: a low-trust source still enters the pool and
        # can recover; a forged profile's relevance advantage is what is taxed.
        adjusted = {sid: float(ranking.scores.get(sid, 0.0)) + config.trust_weight * (trust.get(sid, 0.5) - 0.5)
                    for sid in candidates}
        candidates.sort(key=lambda sid: adjusted[sid], reverse=True)
        for sid in candidates:
            decision.steps.append({"source_id": sid, "role": "candidate", "relevance": ranking.scores.get(sid),
                                   "trust": trust.get(sid, 0.5), "adjusted_score": adjusted[sid]})
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

    if config.decoy_policy == "cells":
        if cells is None:
            raise ValueError("decoy_policy='cells' requires cells")
        # Undo the genuine pass: cells are dispatched whole or not at all.
        decision.genuine_source_ids, decision.steps, spent = [], [], []
        cell_of = {sid: tuple(cell) for cell in cells for sid in cell}
        eligible_ids = {p.source_id for p in eligible}
        taken: set[tuple[str, ...]] = set()
        for source_id in candidates:
            if len(decision.genuine_source_ids) >= config.genuine_k:
                break
            cell = cell_of.get(source_id)
            if cell is None:
                decision.excluded[source_id] = "no_cell"
                continue
            if cell in taken:
                decision.genuine_source_ids.append(source_id)
                decision.decoy_source_ids.remove(source_id)
                continue
            members = [m for m in cell if m in eligible_ids]
            cost = fsum(per_source_cost.get(m, 1.0) for m in members)
            already = len(decision.genuine_source_ids) + len(decision.decoy_source_ids)
            if fsum([*spent, cost]) > config.exposure_budget or already + len(members) > config.max_sources:
                decision.excluded[source_id] = "exposure_budget"
                continue
            taken.add(cell)
            spent.append(cost)
            decision.genuine_source_ids.append(source_id)
            for m in members:
                role = "genuine" if m == source_id else "decoy"
                if role == "decoy":
                    decision.decoy_source_ids.append(m)
                decision.steps.append({
                    "source_id": m, "role": role, "relevance": ranking.scores.get(m),
                    "exposure_cost": per_source_cost.get(m, 1.0), "cumulative_exposure": fsum(spent), "cell": list(cell),
                })
        decision.exposure_spent = fsum(spent)
        dispatched = [*decision.genuine_source_ids, *decision.decoy_source_ids]
        (order_rng or random.Random()).shuffle(dispatched)
        decision.dispatched_source_ids = dispatched
        decision.stop_reason = ("max_sources" if len(dispatched) >= config.max_sources else
                                "exposure_budget" if any(r == "exposure_budget" for r in decision.excluded.values()) else
                                "no_candidates" if not dispatched else "candidates_exhausted")
        return decision

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
