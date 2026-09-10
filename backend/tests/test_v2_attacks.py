"""Tests for the v2 A1 and A3 measurement harnesses (docs/32).

These check the harnesses measure what they claim on synthetic data. They do
not assert that either defence works — that is what the experiments report.
"""
from __future__ import annotations

import numpy as np
import pytest

from baselines.base import SourceProfile
from eval.run_v2_a1 import run_sigma
from eval.run_v2_a3 import ATTACKER_ID, build_attacker, run_condition
from nodes.embedding import HashingEmbedder
from router.v2 import V2Config


def _fixture(n: int = 6, dim: int = 32):
    embedder = HashingEmbedder(n_features=dim)
    node_docs = {
        f"s{i}": [f"topic{i} document about subject {i} number {j}" for j in range(4)]
        for i in range(n)
    }
    profiles = {
        sid: SourceProfile(source_id=sid, centroids=embedder.embed(texts).mean(axis=0, keepdims=True))
        for sid, texts in node_docs.items()
    }
    query_texts, query_vectors, relevant = {}, {}, {}
    for i, sid in enumerate(node_docs):
        for suffix in ("a", "b"):
            qid = f"q{i}{suffix}"
            text = f"topic{i} subject {i}"
            vector = embedder.embed_one(text)
            norm = np.linalg.norm(vector)
            query_texts[qid] = text
            query_vectors[qid] = vector / norm if norm else vector
            relevant[qid] = {sid}
    return embedder, node_docs, profiles, query_texts, query_vectors, relevant


CONFIG = V2Config(exposure_budget=4.0, max_sources=4, genuine_k=2, coarse_k=6, aggregation="max")


# --- A1 ---------------------------------------------------------------------


def test_a1_recovers_the_query_perfectly_without_noise():
    """sigma=0 dispatches the exact query vector, so nearest-neighbour
    inversion against a pool containing that query is trivially exact. This is
    the point: v2's vector dispatch is not secrecy.
    """
    embedder, node_docs, profiles, query_texts, query_vectors, relevant = _fixture()
    doc_embeddings = {sid: embedder.embed(texts) for sid, texts in node_docs.items()}
    row = run_sigma(0.0, profiles, doc_embeddings, query_vectors, query_texts, relevant,
                    config=CONFIG, seed=0)
    assert row["a1_exact_recovery"] == 1.0
    assert row["a1_term_recovery"] == 1.0
    assert row["retrieval_agreement"] == 1.0


def test_a1_recovery_falls_as_sigma_rises():
    embedder, node_docs, profiles, query_texts, query_vectors, relevant = _fixture()
    doc_embeddings = {sid: embedder.embed(texts) for sid, texts in node_docs.items()}
    low = run_sigma(0.0, profiles, doc_embeddings, query_vectors, query_texts, relevant,
                    config=CONFIG, seed=0)
    high = run_sigma(2.0, profiles, doc_embeddings, query_vectors, query_texts, relevant,
                     config=CONFIG, seed=0)
    assert high["a1_exact_recovery"] < low["a1_exact_recovery"]


def test_a1_retrieval_agreement_also_falls_as_sigma_rises():
    """Noise cannot buy A1 protection for free — the same perturbation that
    hides the query changes what comes back.
    """
    embedder, node_docs, profiles, query_texts, query_vectors, relevant = _fixture()
    doc_embeddings = {sid: embedder.embed(texts) for sid, texts in node_docs.items()}
    low = run_sigma(0.0, profiles, doc_embeddings, query_vectors, query_texts, relevant,
                    config=CONFIG, seed=0)
    high = run_sigma(2.0, profiles, doc_embeddings, query_vectors, query_texts, relevant,
                     config=CONFIG, seed=0)
    assert high["retrieval_agreement"] < low["retrieval_agreement"]


# --- A3 ---------------------------------------------------------------------


def test_attacker_profile_is_the_generic_query_mean():
    embedder, node_docs, profiles, query_texts, query_vectors, relevant = _fixture()
    attacker = build_attacker(profiles, query_vectors)
    assert attacker.source_id == ATTACKER_ID
    mean = np.mean(np.array(list(query_vectors.values())), axis=0)
    mean = mean / np.linalg.norm(mean)
    assert np.allclose(np.asarray(attacker.centroids)[0], mean)


@pytest.mark.parametrize("condition", ["none", "plausibility", "trust", "both"])
def test_every_a3_condition_reports_the_required_fields(condition):
    embedder, node_docs, profiles, query_texts, query_vectors, relevant = _fixture()
    row = run_condition(condition, profiles, node_docs, query_vectors, relevant, embedder,
                        config=CONFIG, plausibility_threshold=0.9, seed=0)
    assert 0.0 <= row["attacker_selection_rate"] <= 1.0
    assert 0.0 <= row["honest_source_recall"] <= 1.0
    assert row["honest_sources_rejected_at_publish"] >= 0


def test_rejected_attacker_is_never_selected():
    """If the publish-time check rejects the forged profile, it cannot appear
    in any dispatch — the two must stay consistent.
    """
    embedder, node_docs, profiles, query_texts, query_vectors, relevant = _fixture()
    row = run_condition("plausibility", profiles, node_docs, query_vectors, relevant, embedder,
                        config=CONFIG, plausibility_threshold=0.5, seed=0)
    assert row["attacker_registered"] is False
    assert row["attacker_selection_rate"] == 0.0
    assert row["attacker_reject_reason"]


def test_no_defence_condition_lets_the_attacker_register():
    embedder, node_docs, profiles, query_texts, query_vectors, relevant = _fixture()
    row = run_condition("none", profiles, node_docs, query_vectors, relevant, embedder,
                        config=CONFIG, plausibility_threshold=0.9, seed=0)
    assert row["attacker_registered"] is True
    assert row["honest_sources_rejected_at_publish"] == 0
