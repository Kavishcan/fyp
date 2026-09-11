import json
import time

import numpy as np
import pytest

pytest.importorskip("phe")
from privacy.encrypted_scoring import CoordinatorSession, quantize, score_encrypted


@pytest.fixture(scope="module")
def session():
    return CoordinatorSession([.3, -.4, 0., .5], "test-encoder")


def test_scores_match_fixed_point_plaintext(session):
    docs = np.array([[.1, .2, .3, .4], [-.1, .7, 0., -.3], [0., 0., 0., 0.]])
    response = score_encrypted(session.request(), docs, "test-encoder")
    scores = [r["score"] for r in session.decode(response)]
    expected = quantize(docs) @ session.query / 1e12
    np.testing.assert_allclose(scores, expected, atol=1e-12)


def test_randomized_dense_ciphertexts_no_secret_fields(session):
    a, b = session.request(), session.request()
    assert set(a) == {"version", "model", "modulus", "ciphertexts"}
    assert len(a["ciphertexts"]) == 4
    assert all(x != y for x,y in zip(a["ciphertexts"], b["ciphertexts"]))
    assert len(set(map(len,a["ciphertexts"]))) == 1
    assert all(isinstance(x, str) for x in a["ciphertexts"])


@pytest.mark.parametrize("change", ["model", "version", "modulus", "ciphertexts", "extra"])
def test_bad_request_rejected(session, change):
    payload = session.request()
    if change == "ciphertexts":
        payload[change][0] = "0" * len(payload[change][0])
    else:
        payload[change] = "bad"
    with pytest.raises(ValueError):
        score_encrypted(payload, np.ones((1,4)), "test-encoder")


def test_limit_rejects_not_truncates(session):
    with pytest.raises(ValueError):
        score_encrypted(session.request(), np.ones((129,4)), "test-encoder")


def test_score_response_rejects_unexpected_fields(session):
    response = score_encrypted(session.request(), np.ones((1,4)), "test-encoder")
    response["query"] = "do not accept this"
    with pytest.raises(ValueError):
        session.decode(response)


def test_dimensions_and_nonfinite_values_rejected(session):
    with pytest.raises(ValueError):
        score_encrypted(session.request(),np.ones((1,3)),"test-encoder")
    with pytest.raises(ValueError):
        quantize([float("nan")])
    with pytest.raises(ValueError):
        quantize(np.ones(1025))


def test_no_tiny_keys_or_duplicate_response_indices(session):
    payload = session.request()
    payload["modulus"] = "f"
    with pytest.raises(ValueError):
        score_encrypted(payload,np.ones((1,4)),"test-encoder")
    response = score_encrypted(session.request(),np.ones((2,4)),"test-encoder")
    response["scores"][1]["index"] = 0
    with pytest.raises(ValueError):
        session.decode(response)


def test_enabled_api_with_no_sources_does_not_generate(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    import api.app as module
    from api.state import AppState
    monkeypatch.setattr(module,"state",AppState(str(tmp_path / "audit.jsonl")))
    monkeypatch.setenv("ENABLE_PRIVATE_SCORING","1")
    response = TestClient(module.app).post("/query/private-score",json={"question":"private query"})
    assert response.status_code == 200
    assert response.json()["status"] == "encrypted_scoring_only"
    assert not response.json()["nodes_contacted"]
    assert not response.json()["end_to_end_query_privacy"]


def test_encrypted_scoring_over_real_mcp(tmp_path):
    from nodes.embedding import HashingEmbedder, SHARED_ROUTING_MODEL
    from nodes.mcp_client import MCPNodeHandle
    from nodes.profile import embed_documents

    documents = ["tumour chemo protocol", "tax filing invoice", "cardiac response"]
    path = tmp_path / "encrypted-node.json"
    path.write_text(json.dumps(dict(node_id="encrypted-node", documents=documents)))
    embedder = HashingEmbedder(model_name=SHARED_ROUTING_MODEL, n_features=256)
    q = embedder.embed(["tumour chemo protocol"])[0]
    coordinator = CoordinatorSession(q, SHARED_ROUTING_MODEL)
    payload = coordinator.request()
    start = time.perf_counter()
    response = MCPNodeHandle("encrypted-node",path).score_encrypted_query(payload)
    scores = [r["score"] for r in coordinator.decode(response)]
    expected = quantize(embed_documents(documents,embedder)) @ coordinator.query / 1e12
    np.testing.assert_allclose(scores,expected,atol=1e-12)
    assert int(np.argmax(scores)) == 0
    print(json.dumps(dict(mcp_ms=(time.perf_counter()-start)*1000,
                         request_bytes=len(json.dumps(payload).encode()),
                         response_bytes=len(json.dumps(response).encode()),
                         maximum_score_error=float(np.max(np.abs(scores-expected))))))


def test_api_disabled_and_budget_validation(monkeypatch):
    from fastapi.testclient import TestClient
    from api.app import app
    monkeypatch.delenv("ENABLE_PRIVATE_SCORING", raising=False)
    client = TestClient(app)
    assert client.post("/query/private-score",json={"question":"private"}).status_code == 403
    assert client.post("/query/private-score",json={"question":"private","max_sources":0}).status_code == 422


def test_no_generation_no_plaintext_fallback_no_query_log(tmp_path, monkeypatch):
    from api.state import AppState
    from api.private_scoring import PrivateScoreRequest, run_private_scoring
    from nodes.embedding import HashingEmbedder
    import privacy.encrypted_scoring as crypto

    state = AppState(str(tmp_path / "audit.jsonl"))
    state.routing_embedder = HashingEmbedder(n_features=4)
    state.register_node("a",["tumour treatment"],k=1,sigma=0,policy_labels=[])
    def forbidden(*args, **kwargs):
        raise AssertionError("plaintext fallback or generation attempted")
    node = state.nodes["a"]
    monkeypatch.setattr(node,"retrieve_from_text",forbidden)
    monkeypatch.setattr(node,"retrieve_vector",forbidden)
    class Generator:
        generate = forbidden
    state.generator = Generator()
    result = run_private_scoring(state,PrivateScoreRequest(question="tumour treatment",max_sources=1))
    assert result["ranked_documents"] and not result["errors"]
    assert not result["generation_performed"] and not result["fetch_performed"]
    assert not (tmp_path / "audit.jsonl").exists()
    monkeypatch.setattr(crypto,"score_encrypted",lambda *args: (_ for _ in ()).throw(ValueError("failure")))
    result = run_private_scoring(state,PrivateScoreRequest(question="tumour treatment",max_sources=1))
    assert result["errors"] == {"a":"ValueError"}
    assert result["exposure_spent"] == 1 and not result["ranked_documents"]


def test_policy_and_zero_budget_no_contacts(tmp_path):
    from api.state import AppState
    from api.private_scoring import PrivateScoreRequest, run_private_scoring
    state = AppState(str(tmp_path / "audit.jsonl"))
    state.register_node("restricted",["private notes"],k=1,sigma=0,policy_labels=["not-granted"])
    result = run_private_scoring(state,PrivateScoreRequest(question="private notes"))
    assert not result["nodes_contacted"]
    result = run_private_scoring(state,PrivateScoreRequest(question="private notes",exposure_budget=0))
    assert result["exposure_spent"] == 0
