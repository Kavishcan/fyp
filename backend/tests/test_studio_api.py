"""Studio endpoints: demo federation, identity switch, privacy summary, node
status fields, scorecard (docs/43–45). Wiring only; not privacy results."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api import app as app_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    from api.state import AppState

    fresh = AppState(instrumentation_path=str(tmp_path / "q.jsonl"))
    fresh.generator = None
    monkeypatch.setattr(app_module, "state", fresh)
    with TestClient(app_module.app) as c:
        yield c, fresh


def test_demo_federation_registers_hospitals_with_access_control(client):
    c, st = client
    r = c.post("/demo/federation").json()
    assert set(r["nodes"]) == {"st_marys_cardiology", "city_general_oncology", "northside_nutrition"}
    assert {i["client_id"] for i in r["identities"]} == {"demo-no-role", "demo-researcher", "demo-clinician"}
    nodes = {n["node_id"]: n for n in c.get("/nodes").json()}
    n = nodes["st_marys_cardiology"]
    assert n["collections"] == ["clinical_notes", "public", "research"]
    assert n["gated"] is True and n["public_clusters"] >= 1
    assert n["deidentified"] and n["deidentified"].get("REGISTRY", 0) > 0


def test_no_patient_identifier_reaches_any_citation(client):
    c, st = client
    c.post("/demo/federation")
    c.post("/identity", json={"client_id": "demo-clinician"})
    r = c.post("/query", json={"question": "admitted with chest pain troponin raised", "routing_mode": "psi",
                               "max_nodes": 3, "genuine_k": 1, "psi_nprobe": 3}).json()
    text = " ".join(x["document"] for x in r["citations"])
    assert "Amelia Hart" not in text and "@example.invalid" not in text and "MRN 44" not in text


@pytest.mark.parametrize("identity,sees_clinical", [("demo-clinician", True), ("demo-researcher", False), (None, False)])
def test_identity_switch_changes_what_psi_returns(client, identity, sees_clinical):
    c, st = client
    c.post("/demo/federation")
    got = c.post("/identity", json={"client_id": identity}).json()
    assert (got["active"] or {}).get("client_id") == identity
    r = c.post("/query", json={"question": "admitted with chest pain troponin raised antiplatelet", "routing_mode": "psi",
                               "max_nodes": 3, "genuine_k": 1, "psi_nprobe": 4}).json()
    cols = {x["collection"] for x in r["citations"]}
    assert ("clinical_notes" in cols) == sees_clinical
    assert r["privacy"]["node_receives"].startswith("blinded cluster ids")
    assert r["privacy"]["contacts"] == len(r["nodes_contacted"])


def test_unknown_identity_is_404(client):
    c, _ = client
    assert c.post("/identity", json={"client_id": "nobody"}).status_code == 404


def test_privacy_summary_names_the_payload_per_mode(client):
    c, st = client
    c.post("/nodes/register", json={"node_id": "n1", "documents": ["chemo protocol for tumour patients"]})
    for mode, word in (("legacy", "question text"), ("v2", "vector")):
        r = c.post("/query", json={"question": "chemo", "routing_mode": mode, "max_nodes": 1, "genuine_k": 1}).json()
        assert word in r["privacy"]["node_receives"]


def test_scorecard_endpoint_returns_rows(client):
    c, _ = client
    body = c.get("/scorecard").json()
    assert "rows" in body and "sources" in body
    assert any(r["configuration"].startswith("normal cosine router") for r in body["rows"])
