import asyncio

from fastapi.testclient import TestClient

from api import app as app_module
from api.evidence import run_evidence_query
from api.state import AppState
from router.evidence_budget import AllocationConfig


def test_endpoint_is_opt_in_and_authorization_filtered(tmp_path, monkeypatch):
    state = AppState(str(tmp_path / "log.jsonl"))
    state.generator = None
    for sid, policy in [("public", []), ("secret", ["staff"])]:
        state.register_node(sid, ["heart treatment protocol", "heart followup care", "lung treatment"],
                            policy_labels=policy, k=2, sigma=0)
    monkeypatch.setattr(app_module, "state", state)
    client = TestClient(app_module.app)
    response = client.post("/query/evidence", json={"question": "heart treatment", "max_sources": 2,
                                                  "candidate_budget": 2, "final_k": 1})
    assert response.status_code == 200
    data = response.json()
    assert data["nodes_contacted"] == ["public"]
    assert len(data["citations"]) == 1
    assert data["routing_details"]["candidate_slots_spent"] == 2
    assert state.smart_trust.get("public")[1] == 0
    assert client.get(f"/audit/{data['query_id']}").json()["routing_details"]["mode"] == "evidence_budget"
    assert client.post("/query/evidence", json={"question": "x", "candidate_budget": -1}).status_code == 422
    assert client.post("/query/evidence", json={"question": "x", "candidate_budget": True}).status_code == 422


def test_empty_registry(tmp_path):
    state = AppState(str(tmp_path / "empty.jsonl"))
    state.generator = None
    result = run_evidence_query(state, "question", AllocationConfig())
    assert not result["nodes_contacted"]
    assert result["generation_status"] == "no_evidence"
