"""PSI routing mode through AppState and over a real MCP subprocess.

These verify the wiring and the hiding property at the interface — that no
retrieval tool receiving text or a vector is ever called — on synthetic
data. They are not privacy results and say nothing about retrieval quality.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from api.schemas import QueryRequest
from api.state import AppState
from nodes.mcp_client import MCPNodeHandle
from nodes.simulator import InProcessNode


def _docs(topic: int, n: int = 40) -> list[str]:
    return [f"topic{topic} passage {j} about subject {topic} detail {j % 7}" for j in range(n)]


def _state(tmp_path: Path, n_nodes: int = 6) -> AppState:
    state = AppState(instrumentation_path=str(tmp_path / "q.jsonl"))
    state.generator = None
    for i in range(n_nodes):
        state.register_node(node_id=f"n{i}", documents=_docs(i), policy_labels=[], k=2, sigma=0.0)
    return state


def test_psi_mode_returns_citations_within_the_contact_cap(tmp_path):
    state = _state(tmp_path)
    result = state.run_query("topic3 subject 3", max_nodes=4, genuine_k=1, sigma=0.0, routing_mode="psi")
    assert 1 <= len(result["nodes_contacted"]) <= 4
    assert result["citations"]
    assert result["routing_details"]["mode"] == "psi"
    assert result["routing_details"]["dispatch_payload_kind"] == "blinded_cluster_ids_oprf_psi"
    assert "topic3" in " ".join(c["document"] for c in result["citations"])


def test_profiles_publish_cluster_centroids_of_at_least_min_size(tmp_path):
    state = _state(tmp_path)
    profile = state.registry.get("n0")
    assert profile.cluster_centroids is not None
    assert 1 <= len(profile.cluster_centroids) <= 8   # 40 docs / ~10 per cluster


def test_no_text_or_vector_retrieval_tool_is_called_in_psi_mode(tmp_path, monkeypatch):
    """The whole point: the node answers without ever receiving the query."""
    state = _state(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("node received the query")

    monkeypatch.setattr(InProcessNode, "retrieve", forbidden)
    monkeypatch.setattr(InProcessNode, "retrieve_from_text", forbidden)
    monkeypatch.setattr(InProcessNode, "retrieve_vector", forbidden)
    result = state.run_query("topic2 subject 2", max_nodes=3, genuine_k=1, sigma=0.0, routing_mode="psi")
    assert result["citations"]


def test_psi_request_bytes_are_identical_for_every_contact(tmp_path):
    """Genuine and decoy nodes receive payloads of the same shape and size."""
    state = _state(tmp_path)
    state.run_query("topic1 subject 1", max_nodes=4, genuine_k=1, sigma=0.0, routing_mode="psi")
    log = state.instrumentation.read_all()[-1]
    assert len(set(log["bytes_transferred"]["request_per_node"].values())) == 1


def test_fetch_set_bounds_envelopes_delivered_but_still_opens_the_match(tmp_path):
    state = _state(tmp_path)
    state.register_node(node_id="big", documents=_docs(9, n=120), policy_labels=[], k=2, sigma=0.0)
    result = state.run_query("topic9 subject 9", max_nodes=1, genuine_k=1, sigma=0.0,
                             routing_mode="psi", psi_nprobe=1, psi_fetch_set=3)
    assert result["nodes_contacted"] == ["big"]
    info = result["routing_details"]["psi"]["per_node"]["big"]
    assert info["envelopes_delivered"] <= 3
    assert info["envelopes_opened"] == 1
    assert result["citations"][0]["node_id"] == "big"


def test_full_labeled_psi_delivers_every_envelope_and_opens_only_the_probed(tmp_path):
    state = _state(tmp_path)
    state.register_node(node_id="big", documents=_docs(9, n=120), policy_labels=[], k=2, sigma=0.0)
    result = state.run_query("topic9 subject 9", max_nodes=1, genuine_k=1, sigma=0.0,
                             routing_mode="psi", psi_nprobe=2)
    info = result["routing_details"]["psi"]["per_node"]["big"]
    assert info["envelopes_delivered"] == len(state.registry.get("big").cluster_centroids)
    assert info["envelopes_opened"] <= 2
    assert info["passages_disclosed"] < 120


def test_psi_updates_trust_from_decrypted_passages(tmp_path):
    state = _state(tmp_path)
    result = state.run_query("topic0 subject 0", max_nodes=2, genuine_k=1, sigma=0.0, routing_mode="psi")
    for node_id in result["nodes_contacted"]:
        assert state.v2_trust.get(node_id)[1] >= 1


def test_schema_rejects_sigma_in_psi_mode():
    with pytest.raises(ValueError):
        QueryRequest(question="q", routing_mode="psi", sigma=0.5)
    assert QueryRequest(question="q", routing_mode="psi", psi_fetch_set=4).psi_fetch_set == 4


# --- real MCP subprocess ----------------------------------------------------


@pytest.fixture
def mcp_node_file(tmp_path: Path) -> Path:
    spec = {"node_id": "mcp_psi", "local_model": "toy-e5", "documents": _docs(4, n=40)}
    path = tmp_path / "mcp_psi.json"
    path.write_text(json.dumps(spec))
    return path


def test_mcp_profile_carries_signed_cluster_centroids(mcp_node_file, tmp_path):
    state = AppState(instrumentation_path=str(tmp_path / "q.jsonl"))
    state.generator = None
    profile = asyncio.run(state.register_mcp_node_async(mcp_node_file))
    assert profile.cluster_centroids is not None and len(profile.cluster_centroids) >= 1
    assert state.registry.get("mcp_psi") is profile   # publish verified the signature over them


def test_psi_over_real_mcp_never_calls_a_query_carrying_tool(mcp_node_file, tmp_path, monkeypatch):
    state = AppState(instrumentation_path=str(tmp_path / "q.jsonl"))
    state.generator = None
    asyncio.run(state.register_mcp_node_async(mcp_node_file))

    def forbidden(*args, **kwargs):
        raise AssertionError("query-carrying MCP tool called")

    monkeypatch.setattr(MCPNodeHandle, "retrieve_from_text", forbidden)
    monkeypatch.setattr(MCPNodeHandle, "retrieve_vector", forbidden)
    result = state.run_query("topic4 subject 4", max_nodes=1, genuine_k=1, sigma=0.0, routing_mode="psi")
    assert result["nodes_contacted"] == ["mcp_psi"]
    assert result["citations"] and "topic4" in result["citations"][0]["document"]
    log = state.instrumentation.read_all()[-1]
    assert log["stage_latency_ms"]["retrieval_per_node"]["mcp_psi"] > 0
    assert log["bytes_transferred"]["response_per_node"]["mcp_psi"] > 0


def test_mcp_psi_key_persists_across_server_processes(mcp_node_file, tmp_path):
    """Spawn-per-call: two processes must serve the same OPRF key and table,
    or the second call's envelopes would not open with the first's outputs."""
    state = AppState(instrumentation_path=str(tmp_path / "q.jsonl"))
    state.generator = None
    asyncio.run(state.register_mcp_node_async(mcp_node_file))
    assert mcp_node_file.with_suffix(".psi.key").exists()
    r1 = state.run_query("topic4 subject 4", max_nodes=1, genuine_k=1, sigma=0.0, routing_mode="psi")
    r2 = state.run_query("topic4 subject 4", max_nodes=1, genuine_k=1, sigma=0.0, routing_mode="psi")
    assert r1["citations"] and r2["citations"]
