"""Regression tests for the security audit (docs/49): each test replays an
attack that succeeded against a real MCP node before the fix.

These are the audit's probes turned into assertions — not a security
proof, and test counts are not security results.
"""
from __future__ import annotations

import json
import stat
from pathlib import Path

import numpy as np
import pytest

from nodes.mcp_client import MCPNodeHandle, PersistentMCPNodeHandle
from privacy.credentials import ClientPolicy, new_credential, write_allow_list
from privacy.psi import PSIClient


def _node_file(tmp_path: Path, *, gated: bool, budget: int = 2, extra: dict | None = None):
    docs = [f"topic{j % 4} passage {j} about subject {j % 4}" for j in range(60)]
    docs += [{"text": f"clinical note {j} ward {j % 3}", "collection": "clinical_notes"} for j in range(20)]
    data = tmp_path / "node.json"
    data.write_text(json.dumps({"node_id": "node", "local_model": "toy-e5", "documents": docs,
                                "access_policy": {"clinician": ["clinical_notes"]}, **(extra or {})}))
    cred = new_credential("client-1")
    if gated:
        write_allow_list(tmp_path / "node.clients.json", {"client-1": ClientPolicy(cred.key, budget)})
    return data, cred


def _served(handle, cred, n: int) -> int:
    ok = 0
    for i in range(n):
        q = PSIClient.blind([i % 3])
        try:
            handle.psi_evaluate(q.blinded, cred.sign("node", q.blinded))
            ok += 1
        except PermissionError:
            pass
    return ok


def test_budget_holds_across_spawn_per_call_processes(tmp_path):
    """Before: budget 2, six requests, six served (each call a fresh process)."""
    data, cred = _node_file(tmp_path, gated=True, budget=2)
    assert _served(MCPNodeHandle("node", data), cred, 6) == 2


def test_budget_survives_a_node_restart_and_audit_is_on_disk(tmp_path):
    data, cred = _node_file(tmp_path, gated=True, budget=3)
    first = PersistentMCPNodeHandle("node", data)
    try:
        assert _served(first, cred, 2) == 2
    finally:
        first.close()
    second = PersistentMCPNodeHandle("node", data)
    try:
        assert _served(second, cred, 3) == 1                      # 2 already spent before the restart
    finally:
        second.close()
    state = tmp_path / "node.usage.sqlite"
    assert stat.S_IMODE(state.stat().st_mode) == 0o600
    from privacy.credentials import load_authorizer

    audit = load_authorizer("node", tmp_path / "node.clients.json", state_path=state).persisted_audit()
    assert [a["outcome"] for a in audit].count("ok") == 3 and "budget_exhausted" in [a["outcome"] for a in audit]


def test_gated_node_refuses_unauthenticated_text_and_vector_retrieval(tmp_path):
    """Before: retrieve("anything", top_n=100000) returned all 60 public documents."""
    data, _ = _node_file(tmp_path, gated=True)
    handle = MCPNodeHandle("node", data)
    with pytest.raises(PermissionError):
        handle.retrieve_from_text("anything", top_n=100000)
    with pytest.raises(PermissionError):
        handle.retrieve_vector([0.0] * 256, top_n=100000)


def test_open_node_caps_top_n(tmp_path):
    data, _ = _node_file(tmp_path, gated=False)
    assert len(MCPNodeHandle("node", data).retrieve_from_text("anything", top_n=100000)) == 20


def test_encrypted_scoring_tool_is_off_by_default(tmp_path):
    """Before: three chosen-plaintext requests recovered every embedding,
    restricted clinical notes included."""
    data, _ = _node_file(tmp_path, gated=False)
    with pytest.raises(PermissionError):
        MCPNodeHandle("node", data).score_encrypted_query({"version": "x"})


def test_enabled_encrypted_scoring_never_scores_restricted_rows(tmp_path):
    from nodes.embedding import SHARED_ROUTING_MODEL, HashingEmbedder
    from privacy.encrypted_scoring import CoordinatorSession

    data, _ = _node_file(tmp_path, gated=False, extra={"experimental_private_scoring": True})
    q = HashingEmbedder(model_name=SHARED_ROUTING_MODEL, n_features=256).embed(["topic1 passage"])[0]
    session = CoordinatorSession(q, SHARED_ROUTING_MODEL)
    response = MCPNodeHandle("node", data).score_encrypted_query(session.request())
    assert len(response["scores"]) == 60                          # public rows only, never the 20 clinical notes


def test_existing_world_readable_psi_key_is_tightened_on_load(tmp_path):
    from nodes.mcp_server import load_node

    data, _ = _node_file(tmp_path, gated=False)
    key = tmp_path / "node.psi.key"
    load_node(data)
    key.chmod(0o644)
    load_node(data)
    assert stat.S_IMODE(key.stat().st_mode) == 0o600


def test_republishing_under_the_same_key_keeps_earned_trust(tmp_path):
    import asyncio

    from api.state import AppState

    data, _ = _node_file(tmp_path, gated=False)
    state = AppState(instrumentation_path=str(tmp_path / "q.jsonl"))
    state.generator = None
    asyncio.run(state.register_mcp_node_async(data))
    state.v2_trust.observe("node", state.registry.get("node"), np.ones((1, 256)))
    before = state.v2_trust.get("node")
    asyncio.run(state.register_mcp_node_async(data))              # same node, same signing key
    assert state.v2_trust.get("node") == before
