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


def test_repeated_registration_bumps_profile_version(client):
    first = client.post(
        "/nodes/register", json={"node_id": "n1", "documents": ["first version of the corpus"]}
    ).json()
    second = client.post(
        "/nodes/register", json={"node_id": "n1", "documents": ["second version of the corpus"]}
    ).json()
    assert second["profile_version"] > first["profile_version"]
