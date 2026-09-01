"""Tests for eval/sweep.py's data-wrangling functions on tiny synthetic
corpora — no real BEIR download required, matching this project's testing
convention (CLAUDE.md "Testing").
"""
from __future__ import annotations

import json
import random

import numpy as np
import pytest

from eval.sweep import (
    REPO_ROOT,
    build_node_profiles,
    collect_documents,
    load_qrels,
    partition_nodes,
    run_pipeline_condition,
    run_plain_baseline,
    select_queries,
)
from nodes.embedding import HashingEmbedder


@pytest.fixture
def synthetic_corpus_dir(tmp_path):
    corpus_dir = tmp_path / "toycorpus"
    (corpus_dir / "qrels").mkdir(parents=True)

    docs = [
        {"_id": "d1", "title": "", "text": "cats are small furry animals"},
        {"_id": "d2", "title": "", "text": "dogs are loyal furry animals"},
        {"_id": "d3", "title": "", "text": "stock markets rise and fall"},
        {"_id": "d4", "title": "", "text": "interest rates affect stock markets"},
        {"_id": "d5", "title": "", "text": "filler document about nothing much"},
        {"_id": "d6", "title": "", "text": "another filler document here"},
    ]
    with (corpus_dir / "corpus.jsonl").open("w") as f:
        for d in docs:
            f.write(json.dumps(d) + "\n")

    queries = [
        {"_id": "q1", "text": "small furry pets"},
        {"_id": "q2", "text": "stock market interest rates"},
    ]
    with (corpus_dir / "queries.jsonl").open("w") as f:
        for q in queries:
            f.write(json.dumps(q) + "\n")

    with (corpus_dir / "qrels" / "test.tsv").open("w") as f:
        f.write("query-id\tcorpus-id\tscore\n")
        f.write("q1\td1\t1\n")
        f.write("q2\td3\t1\n")
        f.write("q2\td4\t1\n")

    return corpus_dir


def test_load_qrels_only_keeps_positive_scores(synthetic_corpus_dir):
    qrels = load_qrels(synthetic_corpus_dir)
    assert qrels == {"q1": {"d1": 1}, "q2": {"d3": 1, "d4": 1}}


def test_load_qrels_missing_corpus_raises_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="docs/06-datasets.md"):
        load_qrels(tmp_path / "does-not-exist")


def test_select_queries_only_returns_judged_queries(synthetic_corpus_dir):
    qrels = load_qrels(synthetic_corpus_dir)
    selected = select_queries(synthetic_corpus_dir, qrels, n_queries=10, rng=random.Random(0))
    assert set(selected) == {"q1", "q2"}


def test_collect_documents_guarantees_required_ids_present(synthetic_corpus_dir):
    qrels = load_qrels(synthetic_corpus_dir)
    required = {"d1", "d3", "d4"}
    documents = collect_documents(synthetic_corpus_dir, required, target_total=4, rng=random.Random(0))
    assert required.issubset(documents.keys())
    assert len(documents) == 4  # padded with one filler doc


def test_collect_documents_raises_if_required_doc_missing(synthetic_corpus_dir):
    with pytest.raises(ValueError, match="not found"):
        collect_documents(synthetic_corpus_dir, {"does-not-exist"}, target_total=4, rng=random.Random(0))


def test_partition_nodes_covers_every_document_exactly_once():
    documents = {f"d{i}": f"text {i}" for i in range(9)}
    node_docs, node_of_doc = partition_nodes("toy", documents, nodes_per_corpus=3, rng=random.Random(0))
    assert set(node_of_doc) == set(documents)
    assert sum(len(v) for v in node_docs.values()) == 9
    assert set(node_of_doc.values()) == {"toy_1", "toy_2", "toy_3"}


def test_full_pipeline_condition_recovers_the_relevant_node(synthetic_corpus_dir):
    """End-to-end smoke test: two topically distinct nodes, sigma=0 (no noise),
    m=1 (no decoys) — routing must recover the correct node for each query.

    Nodes are built directly (not via partition_nodes' random shuffle) so the
    topic separation is exact and the test isolates the pipeline wiring
    rather than depending on a lucky partition draw.
    """
    qrels = load_qrels(synthetic_corpus_dir)
    rng = random.Random(0)
    queries = select_queries(synthetic_corpus_dir, qrels, n_queries=10, rng=rng)

    node_docs = {
        "animals_node": ["cats are small furry animals", "dogs are loyal furry animals"],
        "finance_node": ["stock markets rise and fall", "interest rates affect stock markets"],
    }
    node_of_doc = {"d1": "animals_node", "d2": "animals_node", "d3": "finance_node", "d4": "finance_node"}
    relevant_nodes = {qid: {node_of_doc[did] for did in qrels[qid]} for qid in queries}

    embedder = HashingEmbedder(n_features=64)
    profiles = build_node_profiles(node_docs, embedder, k=1, seed=0)
    query_vectors = {
        qid: vec / np.linalg.norm(vec) for qid, vec in zip(queries, embedder.embed(list(queries.values())))
    }

    from baselines.cosine_router import CosineRouter

    summary = run_pipeline_condition(
        lambda: CosineRouter(aggregation="max"),
        profiles,
        "test_condition",
        query_vectors,
        relevant_nodes,
        coarse_k=2,
        top_k=1,
        m=1,
        sigma=0.0,
        seed=0,
        instrumentation=_NullInstrumentation(),
    )
    assert summary["final_recall"] == 1.0
    assert summary["coarse_recall"] == 1.0


class _NullInstrumentation:
    def record(self, log):
        pass


_TASR_VENDOR_PATH = REPO_ROOT / "backend" / "vendor" / "routing-hijacking-fedrag"


@pytest.mark.skipif(not _TASR_VENDOR_PATH.exists(), reason="upstream TASR repo not cloned")
def test_run_plain_baseline_with_real_tasr_adapter():
    """run_plain_baseline's top_k must be passed explicitly for TASR — its
    upstream route() treats top_k=0 as "select nothing" (list[:0]), unlike
    oracle/broadcast's "0 means everything" convention.
    """
    from baselines.base import SourceProfile
    from baselines.tasr_adapter import TASRAdapter

    profiles = [
        SourceProfile(source_id="animals_node", centroids=np.array([[1.0, 0.0]])),
        SourceProfile(source_id="finance_node", centroids=np.array([[0.0, 1.0]])),
    ]
    tasr = TASRAdapter()
    tasr.register_sources(profiles)

    query_vectors = {"q1": np.array([1.0, 0.0]), "q2": np.array([0.0, 1.0])}
    relevant_nodes = {"q1": {"animals_node"}, "q2": {"finance_node"}}

    summary = run_plain_baseline(
        tasr, "rung6_tasr_real", query_vectors, relevant_nodes, _NullInstrumentation(), top_k=1
    )
    assert summary["final_recall"] == 1.0
