"""Tests for the legacy/smart/v2 comparison harness (eval/run_mode_comparison.py).

Synthetic sources only. These check the harness measures what it claims —
matched caps, correct bounds, a working A2 observer — not that any mode wins.
"""
from __future__ import annotations

import numpy as np
import pytest

from baselines.base import SourceProfile
from eval.run_mode_comparison import dispatch_for_mode, run_mode


def _profiles(n: int = 8, dim: int = 6) -> dict:
    profiles = {}
    for i in range(n):
        centroid = np.zeros(dim)
        centroid[i % dim] = 1.0
        centroid[(i + 2) % dim] = 0.2
        profiles[f"s{i}"] = SourceProfile(source_id=f"s{i}", centroids=centroid[None, :])
    return profiles


def _queries(profiles: dict, dim: int = 6) -> tuple[dict, dict]:
    query_vectors, relevant = {}, {}
    for i, sid in enumerate(profiles):
        vector = np.zeros(dim)
        vector[i % dim] = 1.0
        # Two queries per source so topics repeat and the A2 observer has signal.
        for suffix in ("a", "b"):
            query_vectors[f"q{i}{suffix}"] = vector
            relevant[f"q{i}{suffix}"] = {sid}
    return query_vectors, relevant


COMMON = dict(max_nodes=4, genuine_k=2, coarse_k=6, seed=0)


@pytest.mark.parametrize("mode", ["legacy", "smart", "v2"])
def test_every_mode_respects_the_shared_contact_cap(mode):
    profiles = _profiles()
    query_vectors, relevant = _queries(profiles)
    result = run_mode(mode, profiles, query_vectors, relevant, sigma=0.0, **COMMON)
    assert result["contacts"] <= COMMON["max_nodes"]


def test_broadcast_contacts_everything_and_always_hits():
    profiles = _profiles()
    query_vectors, relevant = _queries(profiles)
    result = run_mode("broadcast", profiles, query_vectors, relevant, sigma=0.0, **COMMON)
    assert result["contacts"] == len(profiles)
    assert result["source_recall"] == 1.0


def test_oracle_hits_every_query_with_no_audit_cost():
    profiles = _profiles()
    query_vectors, relevant = _queries(profiles)
    result = run_mode("oracle", profiles, query_vectors, relevant, sigma=0.0, **COMMON)
    assert result["source_recall"] == 1.0
    assert result["audit_cost"] == 0.0


def test_smart_dispatches_no_decoys_so_it_contacts_at_most_the_budget():
    profiles = _profiles()
    query_vectors, relevant = _queries(profiles)
    smart = run_mode("smart", profiles, query_vectors, relevant, sigma=0.0, **COMMON)
    v2 = run_mode("v2", profiles, query_vectors, relevant, sigma=0.0, **COMMON)
    # v2 pads to the cap with decoys; smart stops when gain runs out.
    assert smart["contacts"] <= v2["contacts"]


def test_v2_pads_to_the_cap_with_decoys():
    profiles = _profiles()
    query_vectors, relevant = _queries(profiles)
    result = run_mode("v2", profiles, query_vectors, relevant, sigma=0.0, **COMMON)
    assert result["contacts"] == COMMON["max_nodes"]


def test_audit_cost_never_exceeds_contacts():
    profiles = _profiles()
    query_vectors, relevant = _queries(profiles)
    for mode in ("legacy", "smart", "v2", "broadcast"):
        result = run_mode(mode, profiles, query_vectors, relevant, sigma=0.0, **COMMON)
        assert result["audit_cost"] <= result["contacts"]


def test_a2_precision_is_reported_when_topics_repeat():
    profiles = _profiles()
    query_vectors, relevant = _queries(profiles)
    result = run_mode("v2", profiles, query_vectors, relevant, sigma=0.0, **COMMON)
    assert result["a2_topics"] > 0
    assert 0.0 <= result["a2_precision"] <= 1.0


def test_unknown_mode_is_rejected():
    profiles = _profiles()
    with pytest.raises(ValueError, match="unknown mode"):
        dispatch_for_mode("nonsense", np.zeros(6), profiles, "t", set(),
                          max_nodes=4, genuine_k=2, coarse_k=6, sigma=0.0,
                          rng=np.random.default_rng(0))
