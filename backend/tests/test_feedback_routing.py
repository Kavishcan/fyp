import numpy as np
import pytest

from baselines.base import SourceProfile
from router.evidence_budget import AllocationConfig, Candidate, allocate, feedback_query


@pytest.mark.parametrize("budget", [0, 1, 2, 6, 7, 12])
@pytest.mark.parametrize("cap", [0, 1, 3, 10])
def test_zero_feedback_matches_equal_candidates(budget, cap):
    rng = np.random.default_rng(14)
    profiles = [SourceProfile(str(i), rng.normal(size=(3, 8))) for i in range(6)]
    vectors = rng.normal(size=(6, 12, 8))
    calls = []

    def get(sid, offset):
        calls.append((sid, offset))
        return Candidate(sid, f"{sid}-{offset}", "text", vectors[int(sid), offset])

    q = rng.normal(size=8)
    equal = allocate(q, profiles, get, AllocationConfig(cap, budget, method="equal"))
    calls.clear()
    feedback = allocate(q, profiles, get, AllocationConfig(cap, budget, method="feedback", feedback_strength=0))
    assert equal.contacted == feedback.contacted
    assert equal.quotas == feedback.quotas
    assert [p.document_id for p in equal.final] == [p.document_id for p in feedback.final]
    assert len(calls) <= budget
    assert len(feedback.contacted) <= cap


def test_paid_passage_can_change_next_source():
    profiles = [SourceProfile("a", np.array([[1., 0.]])),
                SourceProfile("b", np.array([[.9, -.43]])),
                SourceProfile("c", np.array([[.8, .6]]))]
    calls = []

    def get(sid, offset):
        calls.append((sid, offset))
        return Candidate(sid, f"{sid}-{offset}", "text", np.array([.6, .8]))

    result = allocate(np.array([1., 0.]), profiles, get,
                      AllocationConfig(2, 6, method="feedback", feedback_strength=.5))
    assert result.contacted == ["a", "c"]
    assert result.quotas == {"a": 3, "c": 3}
    assert calls[:2] == [("a", 0), ("c", 0)]
    assert len(calls) == 6


def test_empty_or_unrelated_feedback_preserves_query():
    q = np.array([1., 0.])
    assert np.array_equal(feedback_query(q, [], .5), q)
    assert np.array_equal(feedback_query(q, [Candidate("a", "1", "text", -q)], .5), q)


@pytest.mark.parametrize("strength", [float("nan"), float("inf"), -.1, 1.1, True])
def test_invalid_strength_rejected(strength):
    with pytest.raises(ValueError):
        AllocationConfig(method="feedback", feedback_strength=strength)


def test_failed_opening_is_charged_and_cannot_expand_past_cap():
    profiles = [SourceProfile(str(i), np.array([[1., 0.]])) for i in range(5)]
    result = allocate(np.array([1., 0.]), profiles, lambda s, n: None,
                      AllocationConfig(2, 9, method="feedback"))
    assert len(result.actions) == len(result.contacted) == 2


def test_feedback_mode_reaches_api(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from api import app as module
    from api.state import AppState
    state = AppState(str(tmp_path / "api.jsonl"))
    state.generator = None
    state.register_node("a", ["heart disease", "heart treatment"], policy_labels=[], k=1, sigma=0)
    monkeypatch.setattr(module, "state", state)
    response = TestClient(module.app).post("/query/evidence", json={"question": "heart", "method": "feedback",
                                                                  "feedback_strength": .1, "candidate_budget": 2})
    assert response.status_code == 200
    assert response.json()["routing_details"]["config"]["feedback_strength"] == .1
