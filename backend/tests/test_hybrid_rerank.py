"""Hybrid dense + pool-BM25 rerank (router/hybrid_rerank.py, docs/48).

Checks the scoring behaves as specified and that the API option changes only
device-side ranking — never what a node receives. Not a retrieval-quality
result (docs/48 is).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from api.schemas import QueryRequest
from api.state import AppState
from router.hybrid_rerank import bm25_pool, hybrid_rerank, hybrid_scores, tokenize


def test_tokenizer_drops_function_words_and_keeps_clinical_terms():
    assert tokenize("The patient has elevated Troponin and a STEMI") == ["patient", "elevated", "troponin", "stemi"]


def test_bm25_prefers_documents_sharing_rare_question_terms():
    docs = ["chest pain troponin elevated", "chest pain resolved", "knee injury", "chest pain chest pain"]
    scores = bm25_pool("troponin chest pain", docs)
    assert int(np.argmax(scores)) == 0


def test_weight_zero_is_exactly_the_dense_cosine():
    rng = np.random.default_rng(0)
    e, q = rng.normal(size=(6, 8)), rng.normal(size=8)
    cosine = (e @ q) / (np.linalg.norm(e, axis=1) * np.linalg.norm(q))
    assert np.allclose(hybrid_scores("anything", q, ["d"] * 6, e, weight=0.0), cosine)


def test_lexical_evidence_breaks_a_dense_tie():
    e = np.tile([1.0, 0.0], (3, 1))                      # identical embeddings: dense cannot separate them
    docs = ["unrelated words here", "patient with kawasaki disease", "another unrelated note"]
    ranked = hybrid_rerank("kawasaki disease in a child", np.array([1.0, 0.0]),
                           [{"document": d, "embedding": v} for d, v in zip(docs, e)], top_n=1)
    assert ranked[0][0] == docs[1]


def _state(tmp_path: Path) -> AppState:
    state = AppState(instrumentation_path=str(tmp_path / "q.jsonl"))
    state.generator = None
    for i in range(4):
        docs = [f"topic{i} passage {j} about subject {i}" + (" troponin rise" if j % 5 == 0 else "") for j in range(40)]
        state.register_node(node_id=f"n{i}", documents=docs, policy_labels=[], k=2, sigma=0.0)
    return state


def test_hybrid_changes_only_device_side_ranking(tmp_path):
    state = _state(tmp_path)
    runs = {}
    for mode in ("dense", "hybrid"):
        r = state.run_query("troponin subject 2", max_nodes=3, genuine_k=1, sigma=0.0, routing_mode="blind",
                            blind_probes=4, rerank=mode, evidence_top_k=3)
        runs[mode] = r
    per = {m: {n: v["probes_sent"] for n, v in r["routing_details"]["blind"]["per_node"].items()} for m, r in runs.items()}
    assert per["dense"] == per["hybrid"]                   # identical traffic to every node
    assert "troponin" in runs["hybrid"]["citations"][1]["document"]


def test_request_schema_rerank_field():
    assert QueryRequest(question="q", routing_mode="blind", rerank="hybrid").rerank == "hybrid"
    with pytest.raises(ValueError):
        QueryRequest(question="q", rerank="cross-encoder")
