import pytest

from eval.metrics import audit_cost, coarse_recall_at_k, ndcg_at_k, precision_at_k, recall_at_k, reciprocal_rank


def test_recall_at_k_full_hit():
    assert recall_at_k(["a", "b", "c"], {"a", "b"}, k=3) == 1.0


def test_recall_at_k_partial_hit():
    assert recall_at_k(["a", "x", "y"], {"a", "b"}, k=3) == 0.5


def test_recall_at_k_empty_relevant_set_is_vacuously_full():
    assert recall_at_k(["a"], set()) == 1.0


def test_coarse_recall_matches_recall_computation():
    assert coarse_recall_at_k(["a", "b"], {"a"}, k=2) == recall_at_k(["a", "b"], {"a"}, k=2)


def test_precision_at_k():
    assert precision_at_k(["a", "x"], {"a"}, k=2) == pytest.approx(0.5)


def test_reciprocal_rank_finds_first_relevant():
    assert reciprocal_rank(["x", "a", "b"], {"a", "b"}) == pytest.approx(0.5)


def test_reciprocal_rank_no_hit_is_zero():
    assert reciprocal_rank(["x", "y"], {"a"}) == 0.0


def test_ndcg_perfect_ranking_is_one():
    assert ndcg_at_k(["a", "b"], {"a", "b"}, k=2) == pytest.approx(1.0)


def test_audit_cost_counts_irrelevant_contacts():
    assert audit_cost(["a", "b", "c"], {"a"}) == 2
