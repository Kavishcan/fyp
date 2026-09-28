"""Role-based access to node collections (docs/45). These check that the
node enforces roles inside the PSI step and on the legacy paths; they are
not an access-control audit."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import numpy as np
import pytest

from api.state import AppState
from nodes.embedding import HashingEmbedder
from nodes.signing import generate_private_key, sign_profile, verify_profile
from nodes.simulator import build_simulated_source
from privacy.credentials import Authorizer, ClientPolicy, new_credential, permitted_collections, write_allow_list
from privacy.psi import PSIClient, PSINode

POLICY = {"researcher": ["research"], "clinician": ["research", "clinical_notes"]}


def _docs():
    public = [f"public guideline {i} on healthy diet and exercise" for i in range(20)]
    research = [f"research abstract {i} on statin trial outcomes" for i in range(20)]
    clinical = [f"clinical note {i} chest pain troponin raised admitted cardiology" for i in range(20)]
    docs = public + research + clinical
    cols = ["public"] * 20 + ["research"] * 20 + ["clinical_notes"] * 20
    return docs, cols


def test_permitted_collections_rules():
    avail = ["public", "research", "clinical_notes"]
    assert permitted_collections(POLICY, (), avail, authorised=False) == ["public"]
    assert permitted_collections(POLICY, ("researcher",), avail, authorised=True) == ["public", "research"]
    assert permitted_collections(POLICY, ("clinician",), avail, authorised=True) == ["clinical_notes", "public", "research"]
    assert permitted_collections(POLICY, ("clinician",), avail, authorised=False) == ["public"]   # open node


def test_psi_node_never_opens_a_collection_it_did_not_evaluate():
    node = PSINode("n")
    node.build_table({0: [{"document": "pub"}], 1: [{"document": "clin"}]}, {0: "public", 1: "clinical_notes"})
    q = PSIClient.blind([0, 1])                                   # probe BOTH, including the restricted one
    evaluated = node.evaluate_for(q.blinded, ["public"])          # researcher-without-clinical view
    opened = PSIClient.open_matches_multi(q, evaluated, "n", node.envelopes_for(None))
    assert set(opened) == {0}
    evaluated = node.evaluate_for(q.blinded, ["public", "clinical_notes"])
    assert set(PSIClient.open_matches_multi(q, evaluated, "n", node.envelopes_for(None))) == {0, 1}


def test_single_collection_node_is_byte_compatible():
    node = PSINode("n")
    node.build_table({0: [{"document": "x"}]})
    q = PSIClient.blind([0])
    old = PSIClient.open_matches(q, PSIClient.unblind(q, node.evaluate(q.blinded)), "n", node.envelopes_for(None))
    new = PSIClient.open_matches_multi(q, node.evaluate_for(q.blinded, ["public"]), "n", node.envelopes_for(None))
    assert old == new == {0: [{"document": "x"}]}


def _state_with_node(tmp_path, roles_by_client):
    docs, cols = _docs()
    state = AppState(instrumentation_path=str(tmp_path / "q.jsonl"))
    state.generator = None
    node, profile = build_simulated_source("hosp", docs, state.routing_embedder, k=2, sigma=0.0,
                                           rng=np.random.default_rng(0), collections=cols, access_policy=POLICY)
    creds = {cid: new_credential(cid, roles=tuple(r)) for cid, r in roles_by_client.items()}
    node.authorizer = Authorizer("hosp", {cid: ClientPolicy(c.key, 1000, tuple(roles_by_client[cid])) for cid, c in creds.items()})
    state._publish("hosp", node, profile, "shared")
    return state, creds


@pytest.mark.parametrize("client,sees_clinical", [("clin", True), ("res", False)])
def test_role_decides_whether_clinical_notes_are_served(tmp_path, client, sees_clinical):
    state, creds = _state_with_node(tmp_path, {"clin": ["clinician"], "res": ["researcher"]})
    state.credential = creds[client]
    r = state.run_query("chest pain troponin cardiology admitted", max_nodes=1, genuine_k=1, sigma=0.0,
                        routing_mode="psi", psi_nprobe=3)
    text = " ".join(c["document"] for c in r["citations"])
    assert ("clinical note" in text) == sees_clinical


def test_a_client_lying_about_its_roles_gains_nothing(tmp_path):
    state, creds = _state_with_node(tmp_path, {"res": ["researcher"]})
    liar = new_credential("res", roles=("clinician",))
    state.credential = type(liar)(client_id="res", key=creds["res"].key, roles=("clinician",))
    r = state.run_query("chest pain troponin cardiology admitted", max_nodes=1, genuine_k=1, sigma=0.0,
                        routing_mode="psi", psi_nprobe=3)
    assert not any("clinical note" in c["document"] for c in r["citations"])


def test_legacy_and_v2_paths_never_return_restricted_documents(tmp_path):
    state, _ = _state_with_node(tmp_path, {})
    for mode in ("legacy", "v2"):
        r = state.run_query("chest pain troponin cardiology admitted", max_nodes=1, genuine_k=1, sigma=0.0, routing_mode=mode)
        assert all("clinical note" not in c["document"] and "research abstract" not in c["document"] for c in r["citations"])


def test_access_policy_and_cluster_collections_are_signed():
    docs, cols = _docs()
    node, profile = build_simulated_source("hosp", docs, HashingEmbedder(), k=2, sigma=0.0,
                                           rng=np.random.default_rng(0), collections=cols, access_policy=POLICY)
    key = generate_private_key()
    sign_profile(profile, key)
    assert verify_profile(profile)
    profile.access_policy = {"researcher": ["research", "clinical_notes"]}   # tamper
    assert not verify_profile(profile)


def test_real_mcp_node_enforces_roles_from_its_allow_list(tmp_path: Path):
    docs, cols = _docs()
    data = tmp_path / "hosp.json"
    data.write_text(json.dumps({"node_id": "hosp", "local_model": "toy-e5", "access_policy": POLICY,
                                "documents": [{"text": d, "collection": c} for d, c in zip(docs, cols)]}))
    clin, res = new_credential("clin", ("clinician",)), new_credential("res", ("researcher",))
    write_allow_list(tmp_path / "hosp.clients.json", {"clin": ClientPolicy(clin.key, 1000, ("clinician",)),
                                                      "res": ClientPolicy(res.key, 1000, ("researcher",))})
    state = AppState(instrumentation_path=str(tmp_path / "q.jsonl"))
    state.generator = None
    profile = asyncio.run(state.register_mcp_node_async(data))
    assert profile.access_policy == POLICY and "clinical_notes" in profile.cluster_collections
    seen = {}
    for name, cred in (("clin", clin), ("res", res)):
        state.credential = cred
        r = state.run_query("chest pain troponin cardiology admitted", max_nodes=1, genuine_k=1, sigma=0.0,
                            routing_mode="psi", psi_nprobe=3)
        seen[name] = " ".join(c["document"] for c in r["citations"])
    assert "clinical note" in seen["clin"] and "clinical note" not in seen["res"]
    key_file = json.loads((tmp_path / "hosp.psi.key").read_text())
    assert set(key_file) == {"public", "research", "clinical_notes"}
    assert oct((tmp_path / "hosp.psi.key").stat().st_mode & 0o777) == "0o600"
