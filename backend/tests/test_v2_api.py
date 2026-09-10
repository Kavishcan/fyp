"""v2 routing mode through the API (docs/30).

The load-bearing test here is
`test_v2_never_sends_raw_query_text_to_a_node` — the whole point of the mode.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.state import AppState


@pytest.fixture(autouse=True)
def fresh_state(tmp_path, monkeypatch):
    import api.app as app_module

    fresh = AppState(instrumentation_path=str(tmp_path / "queries.jsonl"))
    monkeypatch.setattr(app_module, "state", fresh)
    yield fresh


@pytest.fixture
def client():
    return TestClient(app)


def _register(client, **nodes) -> None:
    for node_id, document in nodes.items():
        client.post("/nodes/register", json={"node_id": node_id, "documents": [document]})


def test_v2_never_sends_raw_query_text_to_a_node(client, fresh_state):
    """No node — genuine or decoy — may receive the query string in v2."""
    _register(client, a="chemo tumour protocol", b="heart attack response", c="tax filing guidance")
    secret = "chemo tumour protocol for a named patient"

    calls = {}
    for node_id, node in fresh_state.nodes.items():
        calls[node_id] = []
        original = node.retrieve_vector
        node.retrieve_vector = lambda vector, top_n=1, _id=node_id, _orig=original: (
            calls[_id].append(vector) or _orig(vector, top_n=top_n)
        )

    with patch.object(fresh_state.nodes["a"], "retrieve_from_text") as from_text:
        with patch.object(fresh_state.nodes["a"], "retrieve") as by_local_vector:
            body = client.post("/query", json={
                "question": secret, "routing_mode": "v2", "max_nodes": 3, "genuine_k": 1,
            }).json()
            from_text.assert_not_called()      # the raw-text path is never taken
            by_local_vector.assert_not_called()  # nor the local-space path

    assert body["nodes_contacted"]
    for node_id in body["nodes_contacted"]:
        assert calls[node_id], f"{node_id} was contacted but not via retrieve_vector"


def test_v2_sends_an_identical_payload_to_genuine_and_decoy_nodes(client, fresh_state):
    _register(client, a="chemo tumour protocol", b="heart attack response", c="tax filing guidance")
    seen = []
    for node in fresh_state.nodes.values():
        original = node.retrieve_vector
        node.retrieve_vector = lambda vector, top_n=1, _orig=original: (
            seen.append((tuple(float(x) for x in vector), top_n)) or _orig(vector, top_n=top_n)
        )

    body = client.post("/query", json={
        "question": "chemo tumour", "routing_mode": "v2", "max_nodes": 3, "genuine_k": 1,
    }).json()

    details = body["routing_details"]
    assert details["genuine_source_ids"] and details["decoy_source_ids"]
    assert len(seen) == len(body["nodes_contacted"])
    assert len(set(seen)) == 1, "decoy and genuine requests must be indistinguishable"


def test_v2_reports_budget_genuine_and_decoys_in_the_audit(client, fresh_state):
    _register(client, a="chemo tumour", b="heart treatment", c="tax filing")
    body = client.post("/query", json={
        "question": "chemo tumour", "routing_mode": "v2", "max_nodes": 3, "genuine_k": 1,
    }).json()
    details = body["routing_details"]
    assert details["mode"] == "v2"
    assert details["dispatch_payload_kind"] == "shared_routing_space_vector"
    assert details["exposure_spent"] == len(body["nodes_contacted"])

    audit = client.get(f"/audit/{body['query_id']}").json()
    assert set(audit["decoy_source_ids"]) == set(details["decoy_source_ids"])
    assert set(audit["genuine_source_ids"]) == set(details["genuine_source_ids"])


def test_v2_budget_stops_contacts_with_no_genuine_exemption(client, fresh_state):
    _register(client, a="chemo tumour", b="heart treatment", c="tax filing")
    body = client.post("/query", json={
        "question": "chemo tumour", "routing_mode": "v2",
        "max_nodes": 3, "genuine_k": 2, "exposure_budget": 1,
    }).json()
    assert len(body["nodes_contacted"]) == 1
    assert body["routing_details"]["exposure_spent"] == 1
    assert body["routing_details"]["stop_reason"] == "exposure_budget"


def test_v2_zero_budget_contacts_nobody(client, fresh_state):
    _register(client, a="chemo tumour")
    body = client.post("/query", json={
        "question": "chemo tumour", "routing_mode": "v2", "exposure_budget": 0,
    }).json()
    assert body["nodes_contacted"] == []
    assert body["routing_details"]["exposure_spent"] == 0


def test_v2_updates_trust_for_decoys_too_so_the_exemption_cannot_leak(client, fresh_state):
    """The E3 exemption is deliberately off in the API path: with it on, an
    observer of /nodes trust identified decoys at precision/recall 1.00 (E4,
    docs/30). Every contacted source must therefore look the same here.
    """
    _register(client, a="chemo tumour protocol", b="heart attack response", c="tax filing guidance")
    body = client.post("/query", json={
        "question": "chemo tumour", "routing_mode": "v2", "max_nodes": 3, "genuine_k": 1,
    }).json()
    details = body["routing_details"]
    assert details["decoy_source_ids"], "test needs at least one decoy to be meaningful"
    for source_id in body["nodes_contacted"]:
        assert fresh_state.v2_trust.get(source_id)[1] == 1
    assert fresh_state.v2_trust.skipped == {}


def test_v2_leaves_the_smart_and_legacy_trust_stores_untouched(client, fresh_state):
    _register(client, a="chemo tumour", b="heart treatment")
    body = client.post("/query", json={
        "question": "chemo tumour", "routing_mode": "v2", "max_nodes": 2, "genuine_k": 1,
    }).json()
    for source_id in body["nodes_contacted"]:
        assert fresh_state.smart_trust.get(source_id) == (0.5, 0)


def test_v2_rejects_smart_only_knobs(client):
    for payload in (
        {"selection_policy": "relative"},
        {"relevance_mode": "description"},
        {"genuine_k": 4, "max_nodes": 2},
    ):
        response = client.post("/query", json={"question": "q", "routing_mode": "v2", **payload})
        assert response.status_code == 422


def test_v2_accepts_sigma_unlike_smart_mode(client, fresh_state):
    _register(client, a="chemo tumour")
    assert client.post("/query", json={
        "question": "chemo tumour", "routing_mode": "v2", "sigma": 0.1,
    }).status_code == 200
    assert client.post("/query", json={
        "question": "chemo tumour", "routing_mode": "smart", "sigma": 0.1,
    }).status_code == 422


def test_v2_with_no_sources_returns_an_empty_decision(client):
    body = client.post("/query", json={"question": "anything", "routing_mode": "v2"}).json()
    assert body["nodes_contacted"] == []
    assert body["routing_details"]["stop_reason"] == "no_candidates"


def test_legacy_still_default_and_unchanged(client, fresh_state):
    _register(client, a="chemo tumour")
    body = client.post("/query", json={"question": "chemo tumour"}).json()
    assert body["routing_details"] is None      # legacy emits no routing_details
    assert body["nodes_contacted"]
