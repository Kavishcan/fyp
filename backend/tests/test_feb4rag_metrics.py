"""Graded resource-selection metrics for the FeB4RAG harness (docs/36)."""
from __future__ import annotations

import math

import pytest

from eval.run_feb4rag import captured_gain, ndcg_at, reciprocal_rank_of_best, top1_is_best

GRADES = {"a": 20.0, "b": 10.0, "c": 0.0, "d": 5.0}


def test_ndcg_is_one_for_the_ideal_ranking():
    assert ndcg_at(["a", "b", "d", "c"], GRADES, 3) == pytest.approx(1.0)


def test_ndcg_penalises_a_zero_grade_engine_at_the_top():
    assert ndcg_at(["c", "a", "b"], GRADES, 3) < ndcg_at(["a", "b", "c"], GRADES, 3)


def test_ndcg_is_nan_when_nothing_is_relevant():
    assert math.isnan(ndcg_at(["a"], {"a": 0.0, "b": 0.0}, 3))


def test_mrr_and_top1_use_the_maximum_grade_not_any_positive():
    assert reciprocal_rank_of_best(["b", "a"], GRADES) == 0.5   # b is relevant but not best
    assert top1_is_best(["b", "a"], GRADES) == 0.0
    assert top1_is_best(["a", "b"], GRADES) == 1.0


def test_mrr_ties_count_the_first_engine_with_the_top_grade():
    tied = {"a": 20.0, "b": 20.0, "c": 0.0}
    assert reciprocal_rank_of_best(["c", "b", "a"], tied) == 0.5


def test_captured_gain_compares_to_the_best_set_of_equal_size():
    assert captured_gain(["a", "b"], GRADES) == pytest.approx(1.0)
    assert captured_gain(["c", "d"], GRADES) == pytest.approx(5.0 / 30.0)
    assert captured_gain([], GRADES) == 0.0
