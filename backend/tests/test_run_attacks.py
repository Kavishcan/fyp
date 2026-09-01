"""Tests for eval/run_attacks.py on tiny synthetic data — no real BEIR
download required, matching this project's testing convention.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from eval.run_attacks import run_a1_inversion, run_a3_hijack, run_rq03_defense_comparison
from nodes.embedding import HashingEmbedder


def test_a1_inversion_recovers_exact_text_at_zero_sigma():
    embedder = HashingEmbedder(n_features=64)
    queries = {
        "q1": "cats are small furry animals",
        "q2": "stock markets rise and fall",
        "q3": "interest rates affect the economy",
    }
    query_vectors = {qid: embedder.embed_one(text) for qid, text in queries.items()}
    for qid in query_vectors:
        norm = np.linalg.norm(query_vectors[qid])
        query_vectors[qid] = query_vectors[qid] / norm if norm else query_vectors[qid]

    rows = run_a1_inversion(query_vectors, queries, sigmas=[0.0, 2.0], seed=0)

    assert len(rows) == 2
    zero_sigma_row = rows[0]
    assert zero_sigma_row["sigma"] == 0.0
    assert zero_sigma_row["exact_recovery_rate"] == 1.0  # no noise -> nearest neighbour is itself
    assert zero_sigma_row["mean_term_recovery"] == 1.0

    high_sigma_row = rows[1]
    assert 0.0 <= high_sigma_row["exact_recovery_rate"] <= 1.0
    assert 0.0 <= high_sigma_row["mean_term_recovery"] <= 1.0


_TASR_VENDOR_PATH = Path(__file__).resolve().parent.parent / "vendor" / "routing-hijacking-fedrag"


@pytest.mark.skipif(not _TASR_VENDOR_PATH.exists(), reason="upstream TASR repo not cloned")
def test_a3_hijack_runs_against_real_tasr_adapter():
    from baselines.base import SourceProfile

    embedder = HashingEmbedder(n_features=32)
    node_docs = {
        "animals_node": ["cats are small furry animals", "dogs are loyal furry animals"],
        "finance_node": ["stock markets rise and fall", "interest rates affect markets"],
    }
    profiles = {
        node_id: SourceProfile(source_id=node_id, centroids=embedder.embed(texts).mean(axis=0, keepdims=True))
        for node_id, texts in node_docs.items()
    }
    queries = {
        "q1": "furry small animals",
        "q2": "stock market interest rates",
        "q3": "cats and dogs as pets",
        "q4": "economic markets and rates",
    }
    query_vectors = {}
    for qid, text in queries.items():
        vec = embedder.embed_one(text)
        norm = np.linalg.norm(vec)
        query_vectors[qid] = vec / norm if norm else vec

    result = run_a3_hijack(profiles, node_docs, query_vectors, embedder, seed=0)

    assert result["attacker_id"] == "attacker_forged"
    assert result["n_queries"] == 4
    assert 0.0 <= result["overall_selection_rate"] <= 1.0
    assert 0.0 <= result["honest_avg_reputation"] <= 1.0


@pytest.mark.skipif(not _TASR_VENDOR_PATH.exists(), reason="upstream TASR repo not cloned")
def test_rq03_defense_comparison_has_three_conditions_with_a_recall_ceiling():
    from baselines.base import SourceProfile

    embedder = HashingEmbedder(n_features=32)
    node_docs = {
        "animals_node": ["cats are small furry animals", "dogs are loyal furry animals"],
        "finance_node": ["stock markets rise and fall", "interest rates affect markets"],
    }
    profiles = {
        node_id: SourceProfile(source_id=node_id, centroids=embedder.embed(texts).mean(axis=0, keepdims=True))
        for node_id, texts in node_docs.items()
    }
    queries = {
        "q1": "furry small animals",
        "q2": "stock market interest rates",
        "q3": "cats and dogs as pets",
        "q4": "economic markets and rates",
    }
    query_vectors = {}
    for qid, text in queries.items():
        vec = embedder.embed_one(text)
        norm = np.linalg.norm(vec)
        query_vectors[qid] = vec / norm if norm else vec
    relevant_nodes = {
        "q1": {"animals_node"},
        "q2": {"finance_node"},
        "q3": {"animals_node"},
        "q4": {"finance_node"},
    }

    rows = run_rq03_defense_comparison(profiles, node_docs, query_vectors, relevant_nodes, embedder, seed=0)

    conditions = {row["condition"] for row in rows}
    assert conditions == {"no_attacker", "attacker_no_defense", "attacker_with_defense"}
    for row in rows:
        assert 0.0 <= row["overall_recall"] <= 1.0
    no_attacker_row = next(r for r in rows if r["condition"] == "no_attacker")
    assert "overall_attacker_selection_rate" not in no_attacker_row
    for row in rows:
        if row["condition"] != "no_attacker":
            assert 0.0 <= row["overall_attacker_selection_rate"] <= 1.0
