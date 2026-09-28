"""Metric functions of the HyFedRAG comparison harness (docs/46)."""
from __future__ import annotations

import pytest

from eval.run_hyfedrag_compare import mrr, ndcg_at, p_at


def test_mrr_uses_first_relevant_rank():
    assert mrr(["a", "b", "c"], {"b": 1}) == 0.5
    assert mrr(["a", "b"], {"z": 1}) == 0.0


def test_precision_at_k_divides_by_k_not_by_retrieved():
    assert p_at(["a", "b"], {"a": 1}, k=10) == 0.1


def test_ndcg_is_one_for_ideal_graded_order_and_less_otherwise():
    rel = {"a": 2, "b": 1}
    assert ndcg_at(["a", "b"], rel) == pytest.approx(1.0)
    assert ndcg_at(["b", "a"], rel) < 1.0
    assert ndcg_at(["x"], rel) == 0.0
