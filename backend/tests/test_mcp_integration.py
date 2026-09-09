"""End-to-end tests against a REAL MCP server subprocess — not a mock.

Uses a small synthetic data file (not the downloaded BEIR corpora, which
aren't committed and may not be present) so this suite is self-contained.
Each test spawns an actual `python -m nodes.mcp_server` process and talks to
it over the real MCP stdio protocol.
"""
import asyncio
import json
from pathlib import Path

import pytest

from api.state import AppState
from nodes.mcp_client import MCPNodeHandle
from api.evidence import run_evidence_query
from router.evidence_budget import AllocationConfig


@pytest.fixture
def node_data_file(tmp_path: Path) -> Path:
    spec = {
        "node_id": "test_node",
        "local_model": "toy-e5",
        "documents": [
            "chemo protocol for tumour patients",
            "heart attack response protocol",
            "general checkup referral document",
        ],
    }
    path = tmp_path / "test_node.json"
    path.write_text(json.dumps(spec))
    return path


def test_mcp_handle_get_profile_returns_real_computed_profile(node_data_file):
    handle = MCPNodeHandle(node_id="test_node", data_file=node_data_file)
    profile = handle.get_profile()
    assert profile["source_id"] == "test_node"
    assert profile["local_model"] == "toy-e5"
    assert len(profile["centroids"]) >= 1
    assert profile["document_count_bucket"] == "1-100"
    assert "chemo" in profile["topics"]
    assert profile["description"].startswith("Collection topics:")
    assert len(profile["description_embedding"]) == 256
    assert "documents" not in profile


def test_mcp_handle_retrieve_finds_the_relevant_document(node_data_file):
    handle = MCPNodeHandle(node_id="test_node", data_file=node_data_file)
    results = handle.retrieve_from_text("chemo tumour treatment", top_n=1)
    assert len(results) == 1
    assert "chemo" in results[0]["document"].lower()


def test_mcp_pagination_returns_only_requested_page(node_data_file):
    handle = MCPNodeHandle(node_id="test_node", data_file=node_data_file)
    full = handle.retrieve_from_text("chemo tumour treatment", top_n=3)
    page = handle.retrieve_from_text("chemo tumour treatment", top_n=1, offset=1)
    assert page == full[1:2]
    assert handle.retrieve_from_text("chemo tumour treatment", top_n=1, offset=3) == []


def test_evidence_allocator_uses_real_mcp_pagination(node_data_file, tmp_path):
    state = AppState(str(tmp_path / "evidence-mcp.jsonl"))
    state.generator = None
    asyncio.run(state.register_mcp_node_async(node_data_file))
    result = run_evidence_query(state, "chemo tumour protocol", AllocationConfig(1, 2, 2))
    assert result["nodes_contacted"] == ["test_node"]
    assert len(result["citations"]) == 2
    assert [a["offset"] for a in result["routing_details"]["actions"]] == [0, 1]
    assert result["routing_details"]["requests"] == 2


def test_appstate_register_mcp_node_publishes_to_registry(node_data_file):
    state = AppState(instrumentation_path=str(node_data_file.parent / "queries.jsonl"))
    profile = asyncio.run(state.register_mcp_node_async(node_data_file))
    assert profile.source_id == "test_node"
    assert state.registry.get("test_node") is profile
    assert state.node_local_models["test_node"] == "toy-e5"
    statuses = state.node_status()
    assert statuses[0]["transport"] == "mcp"


def test_appstate_load_mcp_nodes_from_dir_registers_all_specs(node_data_file):
    state = AppState(instrumentation_path=str(node_data_file.parent / "queries.jsonl"))
    loaded = asyncio.run(state.load_mcp_nodes_from_dir(node_data_file.parent))
    assert loaded == ["test_node"]


def test_appstate_load_mcp_nodes_from_dir_skips_missing_directory():
    state = AppState(instrumentation_path="/tmp/does-not-matter.jsonl")
    loaded = asyncio.run(state.load_mcp_nodes_from_dir("/nonexistent/path"))
    assert loaded == []


def test_mcp_profiles_stable_across_fresh_processes(node_data_file):
    handle = MCPNodeHandle(node_id="test_node", data_file=node_data_file)
    assert handle.get_profile() == handle.get_profile()


def test_mcp_metadata_opt_out(node_data_file):
    spec = json.loads(node_data_file.read_text())
    spec["publish_metadata"] = False
    node_data_file.write_text(json.dumps(spec))
    profile = MCPNodeHandle(node_id="test_node", data_file=node_data_file).get_profile()
    assert profile["description"] == ""
    assert profile["description_embedding"] is None


def test_mcp_profile_size_is_configurable(node_data_file):
    spec = json.loads(node_data_file.read_text())
    spec["documents"] = [f"document topic {i}" for i in range(20)]
    spec["k"] = 16
    node_data_file.write_text(json.dumps(spec))
    profile = MCPNodeHandle(node_id="test_node", data_file=node_data_file).get_profile()
    assert len(profile["centroids"]) == 16


@pytest.mark.parametrize("k", [0, -1, 1.5, True])
def test_mcp_invalid_profile_size_rejected(node_data_file, k):
    from nodes.mcp_server import load_node
    spec = json.loads(node_data_file.read_text())
    spec["k"] = k
    node_data_file.write_text(json.dumps(spec))
    with pytest.raises(ValueError, match="positive integer"):
        load_node(node_data_file)


def test_run_query_dispatches_to_a_real_mcp_node_and_gets_real_citations(node_data_file, tmp_path):
    state = AppState(instrumentation_path=str(tmp_path / "queries.jsonl"))
    asyncio.run(state.register_mcp_node_async(node_data_file))

    result = state.run_query("chemo tumour protocol", max_nodes=1, genuine_k=1, sigma=0.0)

    assert result["nodes_contacted"] == ["test_node"]
    assert len(result["citations"]) == 1
    assert "chemo" in result["citations"][0]["document"].lower()


def test_relative_policy_dispatches_through_real_mcp(node_data_file, tmp_path):
    state = AppState(instrumentation_path=str(tmp_path / "relative.jsonl"))
    state.generator = None
    asyncio.run(state.register_mcp_node_async(node_data_file))
    result = state.run_query("chemo tumour protocol", max_nodes=3, genuine_k=1, sigma=0,
                             routing_mode="smart", selection_policy="relative", aggregation="max",
                             minimum_gain=0, exposure_budget=1)
    assert result["nodes_contacted"] == ["test_node"]
    assert result["routing_details"]["exposure_spent"] == 1
    assert result["citations"]
    assert state.smart_trust.get("test_node")[1] == 1


def test_centered_policy_dispatches_through_real_mcp(node_data_file, tmp_path):
    state = AppState(instrumentation_path=str(tmp_path / "centered.jsonl"))
    state.generator = None
    asyncio.run(state.register_mcp_node_async(node_data_file))
    result = state.run_query("chemo tumour protocol", max_nodes=3, genuine_k=1, sigma=0,
                             routing_mode="smart", selection_policy="relative", relative_score_floor=0,
                             relevance_mode="centered", centering_strength=.25, aggregation="max",
                             minimum_gain=0, exposure_budget=1)
    assert result["nodes_contacted"] == ["test_node"]
    assert result["routing_details"]["exposure_spent"] == 1
    assert result["citations"]
    assert state.smart_trust.get("test_node")[1] == 1
