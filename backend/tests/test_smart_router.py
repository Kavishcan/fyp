import json

import numpy as np
import pytest

from baselines.base import SourceProfile
from router.smart import EvidenceTrust, SmartConfig, SmartRouter, SourceEvidence


def profile(sid, vector):
    return SourceProfile(sid, np.array([vector], dtype=float))


def route(profiles, *, evidence=None, query=(1, 0), **config):
    evidence = evidence if evidence is not None else {
        p.source_id: SourceEvidence(authorized=True) for p in profiles
    }
    return SmartRouter().route(np.array(query), profiles, evidence, SmartConfig(**config))


def test_duplicate_profiles_stop_without_filling_fixed_k():
    result = route([profile("b", [1, 0]), profile("a", [1, 0])])
    assert result.selected_source_ids == ["a"]
    assert result.stop_reason == "insufficient_gain"
    assert result.exposure_spent == 1


def test_adaptive_selection_accepts_complementary_profiles():
    result = route([profile("a", [1, 0]), profile("b", [0, 1])], query=(1, 1))
    assert result.selected_source_ids == ["a", "b"]
    assert result.stop_reason == "candidates_exhausted"


@pytest.mark.parametrize("budget,expected", [(0, 0), (0.99, 0), (1, 1), (2, 2)])
def test_budget_is_hard_for_all_contacts(budget, expected):
    result = route([profile("a", [1, 0]), profile("b", [0, 1])],
                   query=(1, 1), exposure_budget=budget)
    assert len(result.selected_source_ids) == expected
    assert result.exposure_spent <= budget


def test_affordable_candidate_is_not_blocked_by_expensive_one():
    ps = [profile("expensive", [1, 0]), profile("cheap", [0.8, 0.6])]
    result = route(ps, exposure_budget=0.5, evidence={
        "expensive": SourceEvidence(authorized=True, exposure_cost=2),
        "cheap": SourceEvidence(authorized=True, exposure_cost=0.5),
    })
    assert result.selected_source_ids == ["cheap"]


def test_authorization_and_missing_evidence_fail_closed():
    result = route([profile("a", [1, 0]), profile("b", [1, 0])], evidence={
        "a": SourceEvidence(authorized=False),
    })
    assert result.selected_source_ids == []
    assert len(result.excluded) == 2


def test_uncertain_trust_is_penalized_and_self_report_is_ignored():
    ps = [profile("new", [1, 0]), profile("observed", [1, 0])]
    ps[0].trust_mean = 1.0
    ps[0].trust_observations = 100000
    result = route(ps, minimum_trust=0.45, evidence={
        "new": SourceEvidence(authorized=True),
        "observed": SourceEvidence(authorized=True, observations=99),
    })
    assert result.selected_source_ids == ["observed"]
    assert result.excluded["new"] == "insufficient_trust"


def test_malformed_profile_is_excluded_and_zero_vectors_do_not_route():
    result = route([profile("bad", [1, 0, 0]), profile("nan", [np.nan, 0]),
                    profile("zero", [0, 0])])
    assert result.selected_source_ids == []
    assert result.excluded["bad"] == result.excluded["nan"] == "invalid_profile"
    assert route([profile("a", [1, 0])], query=(0, 0)).selected_source_ids == []


def test_zero_cap_and_no_sources():
    assert route([profile("a", [1, 0])], max_sources=0).stop_reason == "max_sources"
    assert route([]).stop_reason == "no_eligible_sources"


def test_mean_and_max_are_explicit_ablation_settings():
    p = SourceProfile("a", np.array([[1, 0], [0, 1]]))
    mean = route([p], aggregation="mean")
    maximum = route([p], aggregation="max")
    assert mean.steps[0]["relevance"] == 0.5
    assert maximum.steps[0]["relevance"] == 1


@pytest.mark.parametrize("kwargs", [
    {"exposure_budget": -1}, {"exposure_budget": np.nan},
    {"max_sources": -1}, {"max_sources": 1.5}, {"minimum_gain": np.inf},
    {"minimum_trust": 2}, {"aggregation": "unknown"},
])
def test_invalid_config_rejected(kwargs):
    with pytest.raises(ValueError):
        SmartConfig(**kwargs)


@pytest.mark.parametrize("kwargs", [
    {"trust": np.nan}, {"exposure_cost": 0}, {"exposure_cost": -1},
    {"exposure_cost": np.inf}, {"observations": -1},
])
def test_invalid_evidence_rejected(kwargs):
    with pytest.raises(ValueError):
        SourceEvidence(**kwargs)


def test_invalid_query_and_duplicate_ids_rejected():
    with pytest.raises(ValueError):
        route([], query=(np.nan, 0))
    with pytest.raises(ValueError):
        route([profile("a", [1, 0]), profile("a", [0, 1])])


def test_randomized_budget_cap_and_determinism():
    rng = np.random.default_rng(42)
    for _ in range(50):
        ps = [profile(str(i), rng.normal(size=8)) for i in range(30)]
        evidence = {p.source_id: SourceEvidence(
            authorized=bool(rng.integers(0, 2)), exposure_cost=float(rng.uniform(0.1, 3)),
        ) for p in ps}
        query = rng.normal(size=8)
        result = route(ps, evidence=evidence, query=query, exposure_budget=2.5, max_sources=4)
        reverse = route(list(reversed(ps)), evidence=evidence, query=query,
                        exposure_budget=2.5, max_sources=4)
        assert result.selected_source_ids == reverse.selected_source_ids
        assert len(result.selected_source_ids) <= 4
        assert result.exposure_spent <= 2.5
        assert all(evidence[s].authorized for s in result.selected_source_ids)
        assert sum(evidence[s].exposure_cost for s in result.selected_source_ids) == pytest.approx(result.exposure_spent)
        json.dumps(result.to_dict(), allow_nan=False)


def test_thousand_virtual_profiles_budget_invariant():
    rng = np.random.default_rng(7)
    ps = [profile(str(i), rng.normal(size=16)) for i in range(1000)]
    result = route(ps, query=rng.normal(size=16), exposure_budget=3, max_sources=10)
    assert len(result.selected_source_ids) <= 3
    assert result.exposure_spent <= 3


def test_trust_uses_coordinator_embedding_consistency_and_resets():
    trust = EvidenceTrust()
    p = profile("a", [1, 0])
    assert trust.get("a") == (0.5, 0)
    trust.observe("a", p, np.array([[0, 1]]))
    assert trust.get("a") == (pytest.approx(1 / 3), 1)
    trust.observe("a", p, np.array([[1, 0]]))
    assert trust.get("a") == (0.5, 2)
    trust.observe("a", p, np.empty((0, 0)))
    assert trust.get("a") == (0.4, 3)
    trust.reset("a")
    assert trust.get("a") == (0.5, 0)
