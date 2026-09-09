from dataclasses import replace

import numpy as np
import pytest

from baselines.base import SourceProfile
from router.centering import center_profiles, center_query
from router.smart import SmartConfig, SmartRouter, SourceEvidence


def config(**kwargs):
    return SmartConfig(relevance_mode="centered", selection_policy="relative",
                       relative_score_floor=0, minimum_gain=0, uncertainty_penalty=0,
                       aggregation="max", **kwargs)


@pytest.mark.parametrize("strength", [-1, 1.1, float("nan"), float("inf")])
def test_invalid_strength(strength):
    with pytest.raises(ValueError):
        config(centering_strength=strength)
    with pytest.raises(ValueError):
        center_profiles({}, strength)


def test_background_is_source_balanced():
    a = np.array([[1., 0.]])
    b = np.array([[0., 1.]])
    offset, _ = center_profiles({"a": a, "b": b}, 1)
    repeated, _ = center_profiles({"a": np.repeat(a, 10, axis=0), "b": b}, 1)
    np.testing.assert_allclose(offset, [.5, .5])
    np.testing.assert_allclose(offset, repeated)


def test_zero_vectors_stay_zero():
    offset, profiles = center_profiles({"a": np.array([[1., 0.], [0., 0.]])}, 1)
    assert not profiles["a"][1].any()
    assert not center_query(np.zeros(2), offset).any()


def test_zero_strength_matches_raw_router():
    rng = np.random.default_rng(73)
    profiles = [SourceProfile(str(i), rng.normal(size=(4, 8))) for i in range(20)]
    evidence = {p.source_id: SourceEvidence(authorized=True) for p in profiles}
    query = rng.normal(size=8)
    cfg = config(centering_strength=0)
    result = SmartRouter().route(query, profiles, evidence, cfg)
    raw = SmartRouter().route(query, profiles, evidence, replace(cfg, relevance_mode="centroid"))
    assert result.selected_source_ids == raw.selected_source_ids
    np.testing.assert_allclose([s["relevance"] for s in result.steps], [s["relevance"] for s in raw.steps])


def test_excluded_profiles_cannot_change_background():
    profiles = [SourceProfile("a", np.array([[1., 0.]])), SourceProfile("b", np.array([[0., 1.]]))]
    evidence = {p.source_id: SourceEvidence(authorized=True, trust=1) for p in profiles}
    cfg = config(minimum_trust=.2)
    result = SmartRouter().route(np.array([1., .2]), profiles, evidence, cfg)
    profiles += [SourceProfile("unauthorized", np.array([[1., .8]])),
                 SourceProfile("untrusted", np.array([[1., .9]])),
                 SourceProfile("invalid", np.ones((2, 5)))]
    evidence.update(untrusted=SourceEvidence(authorized=True, trust=0), invalid=SourceEvidence(authorized=True))
    extra = SmartRouter().route(np.array([1., .2]), profiles, evidence, cfg)
    assert result.steps == extra.steps
    assert len(extra.excluded) == 3


def test_offline_transform_matches_production_and_weighted_budget():
    rng = np.random.default_rng(99)
    for _ in range(20):
        profiles = [SourceProfile(str(i), rng.normal(size=(4, 8))) for i in range(30)]
        evidence = {p.source_id: SourceEvidence(authorized=True, trust=1,
                    exposure_cost=float(rng.uniform(.1, 2))) for p in profiles}
        query = rng.normal(size=8)
        cfg = config(exposure_budget=2.5, max_sources=4, centering_strength=.75)
        result = SmartRouter().route(query, profiles, evidence, cfg)
        reverse = SmartRouter().route(query, list(reversed(profiles)), evidence, cfg)
        assert result.steps == reverse.steps
        assert result.exposure_spent <= 2.5
        assert len(result.steps) <= 4
        offset, centered = center_profiles({p.source_id: p.centroids for p in profiles}, .75)
        q = center_query(query, offset)
        for step in result.steps:
            assert step["relevance"] == pytest.approx(np.clip(centered[step["source_id"]] @ q, 0, 1).max())


def test_zero_query_abstains_in_production():
    profile = SourceProfile("a", np.eye(2))
    result = SmartRouter().route(np.zeros(2), [profile], {"a": SourceEvidence(authorized=True)}, config())
    assert not result.selected_source_ids


def test_api_request_validates_centered_option():
    from api.schemas import QueryRequest
    request = QueryRequest(question="test", routing_mode="smart", relevance_mode="centered", centering_strength=.75)
    assert request.centering_strength == .75
    with pytest.raises(ValueError):
        QueryRequest(question="test", relevance_mode="centered")
    with pytest.raises(ValueError):
        QueryRequest(question="test", routing_mode="smart", relevance_mode="centered", centering_strength=2)
