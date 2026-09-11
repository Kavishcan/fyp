"""Tests for the scaling / transport harnesses and the request instrumentation
(docs/33). They check the harnesses measure what they claim on synthetic data;
they say nothing about how the router scales — that is what the experiment
reports.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from api.state import AppState
from baselines.base import SourceProfile
from eval.embed_cache import CachedEmbedder
from eval.run_mcp_transport import summarise
from eval.run_scaling import request_bytes_for, run_mode_at_scale
from nodes.embedding import HashingEmbedder
from nodes.mcp_client import MCPNodeHandle


def _fixture(n: int = 8, dim: int = 32):
    embedder = HashingEmbedder(n_features=dim)
    node_docs = {f"s{i}": [f"topic{i} document about subject {i} number {j}" for j in range(4)] for i in range(n)}
    profiles = {
        sid: SourceProfile(source_id=sid, centroids=embedder.embed(texts).mean(axis=0, keepdims=True))
        for sid, texts in node_docs.items()
    }
    queries, vectors, relevant = {}, {}, {}
    for i, sid in enumerate(node_docs):
        for suffix in ("a", "b"):
            qid = f"q{i}{suffix}"
            text = f"topic{i} subject {i}"
            vec = embedder.embed_one(text)
            norm = np.linalg.norm(vec)
            queries[qid], vectors[qid], relevant[qid] = text, vec / norm if norm else vec, {sid}
    return profiles, queries, vectors, relevant


# --- scaling harness --------------------------------------------------------


@pytest.mark.parametrize("mode", ["broadcast", "oracle", "smart", "v2", "legacy"])
def test_every_mode_reports_latency_and_bytes(mode):
    profiles, queries, vectors, relevant = _fixture()
    row = run_mode_at_scale(mode, profiles, queries, vectors, relevant,
                            max_nodes=4, genuine_k=2, coarse_k=6, seed=0)
    assert row["sources"] == 8
    assert row["routing_latency_ms"] >= 0.0
    assert row["routing_latency_p95_ms"] >= 0.0
    assert row["request_bytes"] > 0.0
    assert 0.0 <= row["source_recall"] <= 1.0


def test_broadcast_contacts_every_source_so_bytes_scale_with_sources():
    small = _fixture(n=4)
    large = _fixture(n=16)
    row_small = run_mode_at_scale("broadcast", *small, max_nodes=4, genuine_k=2, coarse_k=6, seed=0)
    row_large = run_mode_at_scale("broadcast", *large, max_nodes=4, genuine_k=2, coarse_k=6, seed=0)
    assert row_small["contacts"] == 4 and row_large["contacts"] == 16
    assert row_large["request_bytes"] > row_small["request_bytes"]


def test_capped_modes_do_not_grow_bytes_with_sources():
    """The point of a budgeted router: cost is bounded by the cap, not N."""
    small = _fixture(n=8)
    large = _fixture(n=32)
    for mode in ("v2", "smart", "legacy"):
        row_small = run_mode_at_scale(mode, *small, max_nodes=4, genuine_k=2, coarse_k=6, seed=0)
        row_large = run_mode_at_scale(mode, *large, max_nodes=4, genuine_k=2, coarse_k=6, seed=0)
        assert row_small["contacts"] <= 4 and row_large["contacts"] <= 4


def test_v2_request_is_a_vector_and_therefore_larger_than_text():
    vec = np.ones(256) / 16.0
    assert request_bytes_for("v2", "short query", vec) > request_bytes_for("legacy", "short query", vec)
    assert request_bytes_for("legacy", "short query", vec) == len(
        json.dumps({"query": "short query", "top_n": 1}).encode("utf-8")
    )


# --- embedding cache --------------------------------------------------------


class _CountingEmbedder:
    model_name = "counting-test-model"

    def __init__(self) -> None:
        self.calls = 0
        self.inner = HashingEmbedder(n_features=16)

    def embed(self, texts):
        self.calls += 1
        return self.inner.embed(list(texts))


def test_cache_returns_identical_vectors_and_skips_the_model_on_hits(tmp_path: Path):
    inner = _CountingEmbedder()
    cached = CachedEmbedder(inner, cache_dir=tmp_path)
    first = cached.embed(["alpha", "beta"])
    assert inner.calls == 1
    second = cached.embed(["beta", "alpha", "alpha"])
    assert inner.calls == 1  # every text was a hit
    assert np.allclose(second[0], first[1]) and np.allclose(second[1], first[0]) and np.allclose(second[2], first[0])
    # float32 storage: agreement to float32 precision, not bit-identical float64.
    assert np.allclose(first, inner.inner.embed(["alpha", "beta"]), atol=1e-6)
    assert cached.hits == 3 and cached.misses == 2


def test_cache_is_keyed_by_model_name(tmp_path: Path):
    a = _CountingEmbedder()
    b = _CountingEmbedder()
    b.model_name = "another-model"
    CachedEmbedder(a, cache_dir=tmp_path).embed(["alpha"])
    CachedEmbedder(b, cache_dir=tmp_path).embed(["alpha"])
    assert a.calls == 1 and b.calls == 1


# --- api instrumentation ----------------------------------------------------


def _register(state: AppState, node_id: str, documents: list[str]) -> None:
    state.register_node(node_id=node_id, documents=documents, policy_labels=[], k=1, sigma=0.0)


@pytest.mark.parametrize("mode", ["legacy", "smart", "v2"])
def test_query_log_records_stage_latency_and_bytes_per_contact(tmp_path: Path, mode):
    state = AppState(instrumentation_path=str(tmp_path / "q.jsonl"))
    state.generator = None
    for i in range(4):
        _register(state, f"n{i}", [f"topic{i} text {j}" for j in range(3)])
    result = state.run_query("topic1 text", max_nodes=3, genuine_k=1, sigma=0.0, routing_mode=mode)
    log = state.instrumentation.read_all()[-1]
    stages = log["stage_latency_ms"]
    for key in ("embed", "routing", "retrieval_total", "total"):
        assert stages[key] >= 0.0
    assert stages["total"] >= stages["retrieval_total"]
    contacted = result["nodes_contacted"]
    assert set(stages["retrieval_per_node"]) == set(contacted)
    b = log["bytes_transferred"]
    assert set(b["request_per_node"]) == set(contacted)
    assert b["request_total"] == sum(b["request_per_node"].values())
    assert b["response_total"] == sum(b["response_per_node"].values())


def test_v2_request_bytes_are_identical_for_every_contact(tmp_path: Path):
    """Genuine and decoy requests must be byte-identical at the recipient."""
    state = AppState(instrumentation_path=str(tmp_path / "q.jsonl"))
    state.generator = None
    for i in range(6):
        _register(state, f"n{i}", [f"topic{i} text {j}" for j in range(3)])
    state.run_query("topic1 text", max_nodes=4, genuine_k=1, sigma=0.0, routing_mode="v2")
    log = state.instrumentation.read_all()[-1]
    sizes = set(log["bytes_transferred"]["request_per_node"].values())
    assert len(sizes) == 1


def test_text_mode_request_bytes_are_the_raw_question(tmp_path: Path):
    state = AppState(instrumentation_path=str(tmp_path / "q.jsonl"))
    state.generator = None
    _register(state, "n0", ["topic0 text 0"])
    question = "topic0 text"
    state.run_query(question, max_nodes=1, genuine_k=1, sigma=0.0, routing_mode="legacy")
    log = state.instrumentation.read_all()[-1]
    expected = len(json.dumps({"query": question, "top_n": 1}).encode("utf-8"))
    assert log["bytes_transferred"]["request_per_node"]["n0"] == expected


# --- transport summary ------------------------------------------------------


def test_transport_summary_aggregates_per_contact_latency():
    logs = [
        {"dispatched_source_ids": ["a", "b"],
         "stage_latency_ms": {"embed": 1.0, "routing": 2.0, "retrieval_total": 30.0, "total": 33.0,
                              "retrieval_per_node": {"a": 10.0, "b": 20.0}},
         "bytes_transferred": {"request_total": 200, "response_total": 400},
         "extra": {"routing": {"retrieval_errors": {"b": "RuntimeError"}}}},
        {"dispatched_source_ids": ["a"],
         "stage_latency_ms": {"embed": 1.0, "routing": 2.0, "retrieval_total": 40.0, "total": 43.0,
                              "retrieval_per_node": {"a": 40.0}},
         "bytes_transferred": {"request_total": 100, "response_total": 300},
         "extra": {}},
    ]
    row = summarise(logs, mode="v2", registered=5, registration_ms=[500.0, 700.0])
    assert row["queries"] == 2 and row["registered_nodes"] == 5
    assert row["contacts"] == 1.5
    assert row["contact_ms"] == pytest.approx((10 + 20 + 40) / 3)
    assert row["registration_ms_per_node"] == 600.0
    assert row["request_bytes"] == 150.0 and row["response_bytes"] == 350.0
    assert row["retrieval_errors"] == 1


def test_real_mcp_contact_is_timed_and_sized(tmp_path: Path):
    """One genuine subprocess round trip shows up in the log as a timed,
    sized contact — the transport harness relies on exactly this."""
    spec = {"node_id": "t0", "local_model": "toy-e5", "documents": ["chemo protocol", "heart protocol"]}
    data_file = tmp_path / "t0.json"
    data_file.write_text(json.dumps(spec))
    state = AppState(instrumentation_path=str(tmp_path / "q.jsonl"))
    state.generator = None
    import asyncio

    asyncio.run(state.register_mcp_node_async(data_file))
    assert isinstance(state.nodes["t0"], MCPNodeHandle)
    state.run_query("chemo", max_nodes=1, genuine_k=1, sigma=0.0, routing_mode="v2")
    log = state.instrumentation.read_all()[-1]
    assert log["stage_latency_ms"]["retrieval_per_node"]["t0"] > 0.0
    assert log["bytes_transferred"]["response_per_node"]["t0"] > 0
