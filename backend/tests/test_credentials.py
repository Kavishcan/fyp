"""Credential gate on the PSI step (privacy/credentials.py, docs/43)."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from api.state import AppState
from privacy.credentials import (
    Authorizer, ClientPolicy, Credential, Unauthorized, load_authorizer, new_credential, write_allow_list,
)
from privacy.psi import PSIClient, PSINode


def _auth(node_id="n", budget=10):
    cred = new_credential("c1")
    return cred, Authorizer(node_id=node_id, policies={"c1": ClientPolicy(cred.key, budget)})


def test_valid_credential_is_accepted_and_charged():
    cred, authz = _auth()
    q = PSIClient.blind([1, 2])
    assert authz.check(cred.sign("n", q.blinded), q.blinded) == "c1"
    assert authz.remaining("c1") == 8
    assert authz.audit[-1]["outcome"] == "ok" and authz.audit[-1]["evaluations"] == 2


@pytest.mark.parametrize("tamper", ["missing", "unknown", "wrong_node", "wrong_points", "stale", "bad_key"])
def test_refusals_happen_before_any_evaluation(tamper):
    cred, authz = _auth()
    q = PSIClient.blind([1])
    auth = cred.sign("n", q.blinded)
    if tamper == "missing":
        auth = None
    elif tamper == "unknown":
        auth = Credential("nobody", cred.key).sign("n", q.blinded)
    elif tamper == "wrong_node":
        auth = cred.sign("other-node", q.blinded)
    elif tamper == "wrong_points":
        auth = cred.sign("n", PSIClient.blind([1]).blinded)
    elif tamper == "stale":
        auth = cred.sign("n", q.blinded, now=0.0)
    elif tamper == "bad_key":
        auth = Credential("c1", b"\0" * 32).sign("n", q.blinded)
    with pytest.raises(Unauthorized):
        authz.check(auth, q.blinded)
    assert authz.remaining("c1") == 10          # nothing charged
    assert authz.audit[-1]["outcome"] != "ok"


def test_budget_exhaustion_refuses_and_bounds_enumeration():
    cred, authz = _auth(budget=4)
    node = PSINode("n")
    node.build_table({c: [{"document": f"c{c}"}] for c in range(10)})
    opened = set()
    for cid in range(10):
        q = PSIClient.blind([cid])
        try:
            authz.check(cred.sign("n", q.blinded), q.blinded)
        except Unauthorized as exc:
            assert exc.reason == "budget_exhausted"
            break
        out = PSIClient.unblind(q, node.evaluate(q.blinded))
        opened |= set(PSIClient.open_matches(q, out, "n", node.envelopes_for(None)))
    assert len(opened) == 4                     # exactly the daily budget, not the table


def test_allow_list_round_trips_with_owner_only_permissions(tmp_path: Path):
    cred = new_credential("hospital-a-app")
    path = tmp_path / "node.clients.json"
    write_allow_list(path, {"hospital-a-app": ClientPolicy(cred.key, 200)})
    assert oct(path.stat().st_mode & 0o777) == "0o600"
    authz = load_authorizer("n", path)
    q = PSIClient.blind([3])
    assert authz.check(cred.sign("n", q.blinded), q.blinded) == "hospital-a-app"
    assert load_authorizer("n", tmp_path / "absent.json") is None


# --- end to end: gated node over real MCP -------------------------------------


@pytest.fixture
def gated_node(tmp_path: Path):
    docs = [f"topic4 passage {j} about subject 4" for j in range(40)]
    data = tmp_path / "gated.json"
    data.write_text(json.dumps({"node_id": "gated", "local_model": "toy-e5", "documents": docs}))
    cred = new_credential("client-1")
    write_allow_list(tmp_path / "gated.clients.json", {"client-1": ClientPolicy(cred.key, 50)})
    return data, cred


def test_gated_mcp_node_refuses_without_credential_and_serves_with_it(gated_node, tmp_path):
    data, cred = gated_node
    state = AppState(instrumentation_path=str(tmp_path / "q.jsonl"))
    state.generator = None
    asyncio.run(state.register_mcp_node_async(data))
    # No credential: the contact fails closed; psi records it as a retrieval error, no citation.
    r = state.run_query("topic4 subject 4", max_nodes=1, genuine_k=1, sigma=0.0, routing_mode="psi")
    assert r["citations"] == []
    assert r["routing_details"]["retrieval_errors"] == {"gated": "PermissionError"}
    # With the federation credential: served.
    state.credential = cred
    r = state.run_query("topic4 subject 4", max_nodes=1, genuine_k=1, sigma=0.0, routing_mode="psi")
    assert r["citations"] and "topic4" in r["citations"][0]["document"]


def test_gated_simulated_node_enforces_daily_budget(tmp_path):
    state = AppState(instrumentation_path=str(tmp_path / "q.jsonl"))
    state.generator = None
    state.register_node(node_id="g", documents=[f"topic1 passage {j}" for j in range(40)], policy_labels=[], k=1, sigma=0.0)
    cred = new_credential("c")
    state.nodes["g"].authorizer = Authorizer("g", {"c": ClientPolicy(cred.key, daily_evaluation_budget=1)})  # one probe per day
    state.credential = cred
    ok = state.run_query("topic1 passage", max_nodes=1, genuine_k=1, sigma=0.0, routing_mode="psi", psi_nprobe=1)
    assert ok["citations"]
    refused = state.run_query("topic1 passage", max_nodes=1, genuine_k=1, sigma=0.0, routing_mode="psi", psi_nprobe=1)
    assert refused["citations"] == [] and refused["routing_details"]["retrieval_errors"] == {"g": "PermissionError"}
    assert state.nodes["g"].authorizer.audit[-1]["outcome"] == "budget_exhausted"
