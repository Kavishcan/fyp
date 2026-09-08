import numpy as np
import pytest

from baselines.base import SourceProfile
from router.smart import SmartConfig, SmartRouter, SourceEvidence


def decide(vectors, **kwargs):
    profiles = [SourceProfile(str(i), np.asarray([v])) for i, v in enumerate(vectors)]
    evidence = {p.source_id: SourceEvidence(authorized=True) for p in profiles}
    return SmartRouter().route(np.array([1., 0.]), profiles, evidence,
                               SmartConfig(selection_policy="relative", **kwargs))


def test_similar_profiles_do_not_force_early_stop():
    result = decide([[1., 0.]] * 4, exposure_budget=3)
    assert result.selected_source_ids == ["0", "1", "2"]
    assert result.exposure_spent == 3


def test_relative_floor_stops_weak_candidates():
    result = decide([[1., 0.], [.9, np.sqrt(.19)], [.5, np.sqrt(.75)]])
    assert result.selected_source_ids == ["0", "1"]
    assert result.stop_reason == "relative_score_floor"


def test_zero_floor_matches_positive_ranked_budget_control():
    result = decide([[.2, .98], [1., 0.], [.5, .866]], exposure_budget=2,
                    relative_score_floor=0, minimum_gain=0)
    assert result.selected_source_ids == ["1", "2"]


def test_unaffordable_best_does_not_set_relative_reference():
    profiles = [SourceProfile("a", np.array([[1., 0.]])),
                SourceProfile("b", np.array([[.1, .995]]))]
    evidence = {"a": SourceEvidence(authorized=True, exposure_cost=2),
                "b": SourceEvidence(authorized=True)}
    result = SmartRouter().route(np.array([1., 0.]), profiles, evidence,
                               SmartConfig(selection_policy="relative", exposure_budget=1, minimum_gain=0))
    assert result.selected_source_ids == ["b"]


@pytest.mark.parametrize("kwargs", [{"selection_policy": "bad"},
                                     {"relative_score_floor": -1},
                                     {"relative_score_floor": float("nan")}])
def test_invalid_relative_settings(kwargs):
    with pytest.raises(ValueError):
        SmartConfig(**kwargs)


def test_relative_randomized_budget_determinism_authorization():
    rng = np.random.default_rng(90)
    for _ in range(30):
        profiles = [SourceProfile(str(i), rng.normal(size=(4, 8))) for i in range(30)]
        evidence = {p.source_id: SourceEvidence(authorized=i % 4 != 0,
                     exposure_cost=float(rng.uniform(.1, 2))) for i, p in enumerate(profiles)}
        query = rng.normal(size=8)
        config = SmartConfig(selection_policy="relative", exposure_budget=2.5, max_sources=4)
        decision = SmartRouter().route(query, profiles, evidence, config)
        reverse = SmartRouter().route(query, list(reversed(profiles)), evidence, config)
        assert decision.selected_source_ids == reverse.selected_source_ids
        assert len(decision.selected_source_ids) <= 4
        assert decision.exposure_spent <= 2.5
        assert all(evidence[s].authorized for s in decision.selected_source_ids)


def test_relative_zero_query_abstains():
    p = SourceProfile("a", np.eye(2))
    decision = SmartRouter().route(np.zeros(2), [p], {"a": SourceEvidence(authorized=True)},
                                  SmartConfig(selection_policy="relative", minimum_gain=0))
    assert not decision.selected_source_ids
