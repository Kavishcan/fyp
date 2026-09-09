import numpy as np
import pytest

from baselines.base import SourceProfile
from baselines.profile_fusion import fusion_scores, run_control
from eval.run_strong_controls import GRID, choose_controls
from router.evidence_budget import Candidate
from router.lexical_profile import build_sketch, fuse_scores, VERSION


def test_weighted_rrf_equal_weights_reproduces_original_order():
    semantic, lexical = dict(a=.8, b=.7, c=.2), dict(a=.1, b=.9, c=.1)
    old = fuse_scores(semantic, lexical, "rrf")
    new = fusion_scores(semantic, lexical, "weighted_rrf", .5, 60)
    assert sorted(old, key=lambda s: (-old[s], s)) == sorted(new, key=lambda s: (-new[s], s))


@pytest.mark.parametrize("method", ["weighted_rrf", "minmax"])
def test_fusion_endpoints_and_fallback(method):
    semantic, lexical = dict(a=.2, b=.8), dict(a=.5, b=.5)
    assert fusion_scores(semantic, None, method, .5) == semantic
    assert fusion_scores(semantic, lexical, method, 0) == semantic
    assert fusion_scores(semantic, lexical, method, 1)["b"] > fusion_scores(semantic, lexical, method, 1)["a"]


def test_minmax_constant_scores_are_finite():
    assert fusion_scores(dict(a=.5, b=.5), dict(a=.5, b=.5), "minmax", .5) == dict(a=0, b=0)


@pytest.mark.parametrize("weight,constant", [(float("nan"), 60), (-.1, 60), (True, 60), (.5, 0), (.5, float("inf"))])
def test_invalid_fusion_configuration(weight, constant):
    with pytest.raises(ValueError):
        fusion_scores(dict(a=.5), dict(a=.1), "weighted_rrf", weight, constant)


def test_grid_selection_equal_group_weight_and_ties():
    rows = [dict(dataset=d, kind=k, method=m, weight=w, constant=c, candidate_recall=.1)
            for d in ("a", "b") for k in ("random", "topic") for m, w, c in GRID]
    selected = choose_controls(rows)
    assert selected["weighted_rrf"]["weight"] == 0
    assert selected["weighted_rrf"]["constant"] == 10
    rows += [dict(dataset="a", kind="random", method=m, weight=w, constant=c, candidate_recall=.1)
             for m, w, c in GRID] * 3
    assert choose_controls(rows) == selected
    with pytest.raises(ValueError):
        choose_controls(rows[:1])


def test_strong_control_only_contacts_selected_sources_and_charges_requests():
    profiles = [SourceProfile(str(i), np.array([[1., i / 10]]), lexical_sketch=build_sketch([str(i) + " finance"]),
                              lexical_version=VERSION) for i in range(8)]
    calls = []

    def retrieve(s, offset):
        calls.append((s, offset))
        return Candidate(s, f"{s}-{offset}", "text", np.array([1., 0.]))

    result = run_control(np.array([1., 0.]), "finance", profiles, retrieve, "weighted_rrf", .5)
    assert len(result.contacted) == 3
    assert len(calls) == len(result.actions) == 12
    assert set(s for s, _ in calls) == set(result.contacted)
    assert len(result.final) == 5
