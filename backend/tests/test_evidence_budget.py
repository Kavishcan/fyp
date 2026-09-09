import numpy as np
import pytest

from baselines.base import SourceProfile
from router.evidence_budget import AllocationConfig, Candidate, METHODS, allocate, fixed_quotas


def fixture():
    profiles = [SourceProfile("a", np.array([[1., 0.]])),
                SourceProfile("b", np.array([[.8, .6]])),
                SourceProfile("c", np.array([[.6, .8]]))]
    calls = []

    def retrieve(sid, offset):
        calls.append((sid, offset))
        v = next(p.centroids[0] for p in profiles if p.source_id == sid)
        return Candidate(sid, f"{sid}{offset}", f"passage {sid} {offset}", v.copy())
    return profiles, calls, retrieve


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("c,b", [(0, 5), (3, 0), (1, 6), (2, 7), (10, 2)])
def test_budgets_and_offsets(method, c, b):
    profiles, calls, retrieve = fixture()
    result = allocate(np.array([1., 0.]), profiles, retrieve, AllocationConfig(c, b, 3, method))
    assert len(calls) == len(result.actions) <= b
    assert len(result.contacted) <= c
    assert sum(result.quotas.values()) == len(calls)
    for sid, quota in result.quotas.items():
        assert [o for s, o in calls if s == sid] == list(range(quota))
    assert len(result.final) <= 3


def test_feedback_changes_next_source_without_gold_labels():
    profiles, _, retrieve = fixture()
    joint = allocate(np.array([1., 0.]), profiles, retrieve, AllocationConfig(2, 6))
    equal = allocate(np.array([1., 0.]), profiles, retrieve, AllocationConfig(2, 6, method="equal"))
    assert joint.contacted == ["a", "c"]
    assert equal.contacted == ["a", "b"]
    assert joint.quotas != equal.quotas


@pytest.mark.parametrize("mode", ["empty", "error", "invalid"])
def test_failures_are_charged_and_sources_not_retried(mode):
    profiles, _, _ = fixture()

    def retrieve(sid, offset):
        if mode == "error":
            raise RuntimeError("offline")
        if mode == "invalid":
            return Candidate(sid, "bad", "bad", np.array([np.nan, 0.]))
        return None

    result = allocate(np.array([1., 0.]), profiles, retrieve, AllocationConfig(2, 6))
    assert len(result.actions) == 2
    assert result.quotas == {"a": 1, "b": 1}
    assert not result.candidates


def test_duplicates_consume_budget_but_do_not_duplicate_context():
    profiles, _, _ = fixture()
    result = allocate(np.array([1., 0.]), profiles,
                      lambda sid, offset: Candidate(sid, "same", "same text", np.array([1., 0.])),
                      AllocationConfig(3, 8))
    assert result.to_dict()["duplicates"] == 7
    assert result.to_dict()["returned"] == 8
    assert len(result.final) == 1


def test_final_merge_uses_coordinator_cosine_and_not_retrieval_order():
    profiles, _, _ = fixture()
    result = allocate(np.array([1., 0.]), profiles,
                      lambda sid, offset: Candidate(sid, str(offset), str(offset),
                                                    np.array([0., 1.]) if offset == 0 else np.array([1., 0.])),
                      AllocationConfig(1, 2, 1))
    assert result.final[0].document_id == "1"


@pytest.mark.parametrize("value", [-1, 1.5, True])
def test_invalid_config(value):
    with pytest.raises(ValueError):
        AllocationConfig(candidate_budget=value)


def test_zero_query_invalid_profiles_and_duplicate_source_ids():
    profiles, _, retrieve = fixture()
    assert not allocate(np.zeros(2), profiles, retrieve).actions
    profiles += [SourceProfile("bad", np.ones((2, 3)))]
    assert allocate(np.ones(2), profiles, retrieve).skipped_profiles["bad"] == "invalid_profile"
    with pytest.raises(ValueError, match="duplicate"):
        allocate(np.ones(2), profiles + profiles[:1], retrieve)


def test_hamilton_quotas_are_integer_and_budget_exact():
    assert fixed_quotas({"a": .9, "b": .1}, AllocationConfig(2, 10, method="proportional")) == {"a": 8, "b": 2}
    assert fixed_quotas({"a": .9, "b": .1}, AllocationConfig(2, 9, method="equal")) == {"a": 5, "b": 4}


def test_fixed_plans_do_not_reallocate_failed_slots():
    profiles, _, _ = fixture()
    result = allocate(np.array([1., 0.]), profiles,
                      lambda sid, offset: None if sid == "a" else Candidate(sid, str(offset), "text", np.ones(2)),
                      AllocationConfig(2, 6, method="equal"))
    assert result.quotas == {"a": 1, "b": 3}


def test_candidate_source_mismatch_rejected():
    profiles, _, _ = fixture()
    result = allocate(np.ones(2), profiles,
                      lambda sid, offset: Candidate("other", "id", "text", np.ones(2)), AllocationConfig(1, 3))
    assert result.actions[0]["error"] == "ValueError"
    assert not result.candidates
