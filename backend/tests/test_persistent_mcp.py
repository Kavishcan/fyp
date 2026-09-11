"""PersistentMCPNodeHandle: one live server process per node."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from api.state import AppState
from nodes.mcp_client import PersistentMCPNodeHandle


@pytest.fixture
def node_file(tmp_path: Path) -> Path:
    spec = {"node_id": "persist", "local_model": "toy-e5",
            "documents": [f"topic{i % 3} passage {i} about subject {i % 3}" for i in range(30)]}
    path = tmp_path / "persist.json"
    path.write_text(json.dumps(spec))
    return path


def test_persistent_handle_serves_repeated_calls_and_closes(node_file):
    handle = PersistentMCPNodeHandle(node_id="persist", data_file=node_file)
    try:
        profile = handle.get_profile()
        assert profile["source_id"] == "persist"
        first = handle.retrieve_from_text("topic1 subject 1", top_n=1)
        second = handle.retrieve_from_text("topic1 subject 1", top_n=1)
        assert first == second
    finally:
        handle.close()
    handle.close()  # idempotent
    with pytest.raises(RuntimeError):
        handle.get_profile()


def test_persistent_handle_works_from_a_running_event_loop(node_file):
    handle = PersistentMCPNodeHandle(node_id="persist", data_file=node_file)
    try:
        profile = asyncio.run(handle.get_profile_async())
        assert profile["source_id"] == "persist"
    finally:
        handle.close()


def test_appstate_registers_persistent_node_runs_psi_and_closes_on_remove(node_file, tmp_path):
    state = AppState(instrumentation_path=str(tmp_path / "q.jsonl"))
    state.generator = None
    asyncio.run(state.register_mcp_node_async(node_file, persistent=True))
    assert isinstance(state.nodes["persist"], PersistentMCPNodeHandle)
    result = state.run_query("topic2 subject 2", max_nodes=1, genuine_k=1, sigma=0.0, routing_mode="psi")
    assert result["citations"] and "topic2" in result["citations"][0]["document"]
    handle = state.nodes["persist"]
    assert state.remove_node("persist") is True
    with pytest.raises(RuntimeError):
        handle.get_profile()
