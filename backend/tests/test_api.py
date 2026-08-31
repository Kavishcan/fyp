import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.state import AppState


@pytest.fixture(autouse=True)
def fresh_state(tmp_path, monkeypatch):
    """Each test gets a clean AppState so nodes/trust don't leak across tests."""
    import api.app as app_module

    fresh = AppState(instrumentation_path=str(tmp_path / "queries.jsonl"))
    monkeypatch.setattr(app_module, "state", fresh)
    yield fresh


@pytest.fixture
def extra_mcp_node_file(tmp_path, monkeypatch):
    """A synthetic (not downloaded) MCP node spec in a temp "extra" dir,
    with app.EXTRA_MCP_NODES_DIR pointed at it — keeps these tests
    independent of data/mcp_nodes_extra/ actually being populated.
    """
    import api.app as app_module

    extra_dir = tmp_path / "extra"
    extra_dir.mkdir()
    spec = {
        "node_id": "extra_test_node",
        "local_model": "toy-e5",
        "documents": ["chemo protocol for tumour patients"],
    }
    (extra_dir / "extra_test_node.json").write_text(json.dumps(spec))
    monkeypatch.setattr(app_module, "EXTRA_MCP_NODES_DIR", extra_dir)
    return extra_dir


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_register_node_then_appears_in_nodes_list(client):
    resp = client.post(
        "/nodes/register",
        json={"node_id": "hosp_oncology_1", "documents": ["chemo protocol for tumour patients"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["node_id"] == "hosp_oncology_1"

    listing = client.get("/nodes").json()
    assert any(n["node_id"] == "hosp_oncology_1" for n in listing)


def test_query_with_no_registered_nodes_returns_empty_result(client):
    resp = client.post("/query", json={"question": "anything"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["citations"] == []
    assert body["nodes_contacted"] == []


def test_query_returns_relevant_and_decoy_citations(client):
    client.post(
        "/nodes/register",
        json={"node_id": "hosp_onco", "documents": ["chemo protocol for tumour patients"]},
    )
    client.post(
        "/nodes/register",
        json={"node_id": "hosp_cardio", "documents": ["heart attack response protocol"]},
    )
    client.post(
        "/nodes/register",
        json={"node_id": "hosp_general", "documents": ["general checkup referral document"]},
    )

    resp = client.post(
        "/query", json={"question": "tumour chemo protocol", "max_nodes": 3, "genuine_k": 1}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["nodes_contacted"]) == 3
    assert "hosp_onco" in body["nodes_contacted"]
    assert body["answer"] is None
    assert body["generation_status"] == "not_implemented"


def test_audit_endpoint_returns_routing_decision_after_query(client):
    client.post(
        "/nodes/register", json={"node_id": "n1", "documents": ["chemo protocol for tumour"]}
    )
    client.post("/nodes/register", json={"node_id": "n2", "documents": ["heart attack protocol"]})

    query_resp = client.post("/query", json={"question": "tumour chemo", "max_nodes": 2, "genuine_k": 1})
    query_id = query_resp.json()["query_id"]

    audit_resp = client.get(f"/audit/{query_id}")
    assert audit_resp.status_code == 200
    body = audit_resp.json()
    assert body["query_id"] == query_id
    assert "n1" in body["genuine_source_ids"]


def test_audit_endpoint_404_for_unknown_query_id(client):
    resp = client.get("/audit/does-not-exist")
    assert resp.status_code == 404


def test_register_node_defaults_local_model_to_shared_routing_embedder(client):
    resp = client.post(
        "/nodes/register",
        json={"node_id": "n1", "documents": ["chemo protocol for tumour patients"]},
    )
    assert resp.json()["local_model"] == "shared-routing-embedder"


def test_register_node_with_explicit_local_model(client):
    resp = client.post(
        "/nodes/register",
        json={
            "node_id": "n1",
            "documents": ["chemo protocol for tumour patients"],
            "local_model": "toy-bge",
        },
    )
    assert resp.json()["local_model"] == "toy-bge"
    listing = client.get("/nodes").json()
    assert next(n for n in listing if n["node_id"] == "n1")["local_model"] == "toy-bge"


def test_query_retrieves_correctly_across_nodes_with_different_local_models(client):
    """End-to-end: two nodes register with DIFFERENT local embedding models.
    Routing still works (it only ever uses the shared routing embedder), and
    each node's citation is still retrieved correctly from its own space.
    """
    client.post(
        "/nodes/register",
        json={
            "node_id": "hosp_onco",
            "documents": ["chemo protocol for tumour patients"],
            "local_model": "toy-e5",
        },
    )
    client.post(
        "/nodes/register",
        json={
            "node_id": "hosp_cardio",
            "documents": ["heart attack response protocol"],
            "local_model": "toy-bge",
        },
    )

    resp = client.post(
        "/query", json={"question": "tumour chemo protocol", "max_nodes": 2, "genuine_k": 1}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["citations"]) == 2
    onco_citation = next(c for c in body["citations"] if c["node_id"] == "hosp_onco")
    assert onco_citation["document"] == "chemo protocol for tumour patients"
    assert onco_citation["score"] > 0


def test_query_reuses_routing_embedding_when_nodes_share_it(client, fresh_state):
    """Nodes registered without local_model share routing_embedder by object
    identity, so the question must be embedded exactly once per query — not
    once for routing plus once again per dispatched node.
    """
    client.post("/nodes/register", json={"node_id": "n1", "documents": ["chemo protocol for tumour patients"]})
    client.post("/nodes/register", json={"node_id": "n2", "documents": ["heart attack response protocol"]})

    original_embed = fresh_state.routing_embedder.embed
    calls = []

    def counting_embed(texts):
        calls.append(texts)
        return original_embed(texts)

    with patch.object(fresh_state.routing_embedder, "embed", side_effect=counting_embed):
        resp = client.post(
            "/query", json={"question": "tumour chemo protocol", "max_nodes": 2, "genuine_k": 1}
        )

    assert resp.status_code == 200
    assert len(resp.json()["citations"]) == 2  # both nodes still retrieved correctly
    assert len(calls) == 1  # embedded once, reused for both nodes


def test_repeated_registration_bumps_profile_version(client):
    first = client.post(
        "/nodes/register", json={"node_id": "n1", "documents": ["first version of the corpus"]}
    ).json()
    second = client.post(
        "/nodes/register", json={"node_id": "n1", "documents": ["second version of the corpus"]}
    ).json()
    assert second["profile_version"] > first["profile_version"]


def test_list_available_nodes_returns_unregistered_extra_specs(client, extra_mcp_node_file):
    resp = client.get("/nodes/available")
    assert resp.status_code == 200
    body = resp.json()
    assert body == [{"node_id": "extra_test_node", "local_model": "toy-e5", "document_count": 1}]


def test_activate_node_registers_a_real_mcp_server_from_the_extra_dir(client, extra_mcp_node_file):
    resp = client.post("/nodes/activate", json={"node_id": "extra_test_node"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["node_id"] == "extra_test_node"
    assert body["local_model"] == "toy-e5"

    listing = client.get("/nodes").json()
    activated = next(n for n in listing if n["node_id"] == "extra_test_node")
    assert activated["transport"] == "mcp"

    # Once activated it's registered, so it drops off the "available" list.
    available = client.get("/nodes/available").json()
    assert available == []


def test_activate_node_404_for_unknown_node_id(client, extra_mcp_node_file):
    resp = client.post("/nodes/activate", json={"node_id": "does-not-exist"})
    assert resp.status_code == 404
