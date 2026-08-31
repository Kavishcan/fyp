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


def test_mcp_handle_retrieve_finds_the_relevant_document(node_data_file):
    handle = MCPNodeHandle(node_id="test_node", data_file=node_data_file)
    results = handle.retrieve_from_text("chemo tumour treatment", top_n=1)
    assert len(results) == 1
    assert "chemo" in results[0]["document"].lower()


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


def test_run_query_dispatches_to_a_real_mcp_node_and_gets_real_citations(node_data_file, tmp_path):
    state = AppState(instrumentation_path=str(tmp_path / "queries.jsonl"))
    asyncio.run(state.register_mcp_node_async(node_data_file))

    result = state.run_query("chemo tumour protocol", max_nodes=1, genuine_k=1, sigma=0.0)

    assert result["nodes_contacted"] == ["test_node"]
    assert len(result["citations"]) == 1
    assert "chemo" in result["citations"][0]["document"].lower()
