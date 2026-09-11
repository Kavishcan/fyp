"""Privacy-case and enumeration harness metrics (docs/37)."""
from __future__ import annotations

from eval.run_privacy_cases import exposed_fraction
from eval.run_psi_enumeration import simulate


def test_exposed_fraction_counts_values_present_case_insensitively():
    values = ["Test User 001", "test.user001@example.invalid", "TEST-0001"]
    assert exposed_fraction("my name is test user 001 and id TEST-0001", values) == 2 / 3
    assert exposed_fraction("[REDACTED_EMAIL]", values) == 0.0
    assert exposed_fraction("", []) == 0.0


def test_adaptive_enumeration_needs_exactly_clusters_over_nprobe_queries():
    assert simulate(20, 2, adaptive=True, seed=0) == 10
    assert simulate(7, 2, adaptive=True, seed=0) == 4


def test_random_enumeration_is_never_faster_than_adaptive():
    assert simulate(20, 2, adaptive=False, seed=0) >= simulate(20, 2, adaptive=True, seed=0)
