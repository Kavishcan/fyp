"""v2 selection, dispatch indistinguishability and decoy-aware trust (docs/30).

Synthetic vectors only — no corpora, no models. These test the mechanism's
contract, not retrieval quality or any privacy claim.
"""
from __future__ import annotations

import random

import numpy as np
import pytest

from baselines.base import SourceProfile
from router.v2 import (
    DecoyAwareEvidenceTrust,
    V2Config,
    dispatch_payload,
    dispatched_vector,
    select_dispatch,
)


def _profiles(n: int = 6, dim: int = 4) -> list[SourceProfile]:
    profiles = []
    for i in range(n):
        centroid = np.zeros(dim)
        centroid[i % dim] = 1.0
        centroid[(i + 1) % dim] = 0.1 * i
        profiles.append(SourceProfile(source_id=f"s{i}", centroids=centroid[None, :]))
    return profiles


def _query(dim: int = 4) -> np.ndarray:
    q = np.zeros(dim)
    q[0] = 1.0
    return q


def test_dispatch_fills_genuine_then_topic_stable_decoys():
    decision = select_dispatch(
        _query(), _profiles(), trust={}, per_source_cost={}, topic_key="t1",
        config=V2Config(exposure_budget=5, max_sources=5, genuine_k=2, coarse_k=6),
        order_rng=random.Random(0),
    )
    assert len(decision.genuine_source_ids) == 2
    assert len(decision.decoy_source_ids) == 3
    assert set(decision.dispatched_source_ids) == set(decision.genuine_source_ids) | set(decision.decoy_source_ids)
    assert not set(decision.genuine_source_ids) & set(decision.decoy_source_ids)


def test_budget_caps_total_contacts_including_genuine():
    """No genuine-source exemption: an exhausted budget stops genuine contacts
    too, unlike router/exposure.py's legacy `protected` set.
    """
    decision = select_dispatch(
        _query(), _profiles(), trust={}, per_source_cost={},
        topic_key="t1",
        config=V2Config(exposure_budget=1, max_sources=5, genuine_k=2, coarse_k=6),
        order_rng=random.Random(0),
    )
    assert decision.exposure_spent <= 1
    assert len(decision.dispatched_source_ids) == 1
    assert decision.stop_reason == "exposure_budget"


def test_zero_budget_dispatches_nothing():
    decision = select_dispatch(
        _query(), _profiles(), trust={}, per_source_cost={}, topic_key="t1",
        config=V2Config(exposure_budget=0, max_sources=5, genuine_k=2),
    )
    assert decision.dispatched_source_ids == []
    assert decision.exposure_spent == 0


def test_per_source_costs_are_respected():
    costs = {f"s{i}": 3.0 for i in range(6)}
    decision = select_dispatch(
        _query(), _profiles(), trust={}, per_source_cost=costs, topic_key="t1",
        config=V2Config(exposure_budget=7, max_sources=5, genuine_k=2, coarse_k=6),
    )
    assert decision.exposure_spent == 6.0
    assert len(decision.dispatched_source_ids) == 2


def test_nonpositive_cost_is_rejected():
    with pytest.raises(ValueError, match="finite and positive"):
        select_dispatch(
            _query(), _profiles(), trust={}, per_source_cost={"s0": 0.0}, topic_key="t1",
            config=V2Config(),
        )


def test_same_topic_gets_the_same_decoy_set():
    """Topic-stable decoys are what resist the repeated-query intersection
    attack; a fresh random set each time would leak the genuine sources.
    """
    kwargs = dict(trust={}, per_source_cost={}, config=V2Config(exposure_budget=5, max_sources=4, genuine_k=1, coarse_k=6))
    first = select_dispatch(_query(), _profiles(), topic_key="same", **kwargs)
    second = select_dispatch(_query(), _profiles(), topic_key="same", **kwargs)
    assert first.decoy_source_ids == second.decoy_source_ids


def test_minimum_trust_excludes_low_trust_sources():
    decision = select_dispatch(
        _query(), _profiles(), trust={"s0": 0.1}, per_source_cost={}, topic_key="t1",
        config=V2Config(exposure_budget=5, max_sources=5, genuine_k=2, minimum_trust=0.3, coarse_k=6),
    )
    assert "s0" not in decision.dispatched_source_ids
    assert decision.excluded["s0"] == "insufficient_trust"


def test_dispatch_payload_is_identical_for_every_contacted_node():
    """A decoy request must be byte-for-byte indistinguishable from a genuine
    one at the recipient — same vector, same top_n, no role marker.
    """
    vector = dispatched_vector(_query(), sigma=0.0, rng=np.random.default_rng(0))
    payloads = [dispatch_payload(vector, top_n=1) for _ in range(5)]
    assert all(p == payloads[0] for p in payloads)
    assert set(payloads[0]) == {"vector", "top_n"}


def test_dispatched_vector_carries_no_query_text_and_perturbs_only_the_copy():
    query = _query()
    sent = dispatched_vector(query, sigma=0.5, rng=np.random.default_rng(0))
    assert isinstance(sent, np.ndarray)
    assert not np.allclose(sent, query)          # the copy that leaves is perturbed
    assert np.allclose(query, _query())          # routing's own vector is untouched


def test_sigma_zero_dispatches_the_unperturbed_vector():
    query = _query()
    assert np.allclose(dispatched_vector(query, 0.0, np.random.default_rng(0)), query)


def test_decoy_contacts_do_not_move_trust_but_genuine_ones_do():
    trust = DecoyAwareEvidenceTrust()
    profile = SourceProfile(source_id="s0", centroids=np.array([[1.0, 0.0]]))
    passages = np.array([[0.0, 1.0]])  # off-topic for this profile

    trust.observe("s0", profile, passages, is_decoy=True)
    assert trust.get("s0") == (0.5, 0)       # untouched neutral prior
    assert trust.skipped["s0"] == 1

    trust.observe("s0", profile, passages, is_decoy=False)
    assert trust.get("s0")[1] == 1           # genuine contact counted
    assert trust.get("s0")[0] < 0.5          # off-topic evidence lowered it


def test_v2_trust_reset_clears_the_skipped_counter():
    trust = DecoyAwareEvidenceTrust()
    profile = SourceProfile(source_id="s0", centroids=np.array([[1.0, 0.0]]))
    trust.observe("s0", profile, np.array([[1.0, 0.0]]), is_decoy=True)
    trust.reset("s0")
    assert "s0" not in trust.skipped
    assert trust.get("s0") == (0.5, 0)


def test_config_rejects_genuine_k_above_max_sources():
    with pytest.raises(ValueError, match="genuine_k cannot exceed max_sources"):
        V2Config(genuine_k=5, max_sources=2)


def test_no_profiles_returns_empty_decision():
    decision = select_dispatch(_query(), [], trust={}, per_source_cost={}, topic_key="t1")
    assert decision.dispatched_source_ids == []
    assert decision.stop_reason == "no_candidates"
