"""Blind unlock (privacy/blind_unlock.py, docs/47) — protocol, API wiring and
a real MCP node.

These check the mechanism's stated properties at the interface on synthetic
data: every node receives the same number of points whatever the question,
dummies are processed exactly like real points, only chosen envelopes open,
role scoping and budgets still hold, rotated keys lock out cached tables.
They are not privacy measurements (docs/47 is) and say nothing about
retrieval quality.
"""
from __future__ import annotations

import asyncio
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from api.schemas import QueryRequest
from api.state import AppState
from nodes.mcp_client import MCPNodeHandle
from nodes.simulator import InProcessNode
from privacy.blind_unlock import NodeClusters, TableCache, plan_probes, unlock
from privacy.credentials import Authorizer, ClientPolicy, new_credential
from privacy.psi import POINT_BYTES, PSINode, decode_passages, dummy_point, encode_passages

import nacl.bindings as sodium


def _psi_node(node_id: str, n_clusters: int = 5, seed: int = 0) -> PSINode:
    rng = np.random.default_rng(seed)
    node = PSINode(node_id)
    node.build_table({c: [{"document": f"{node_id}-{c}-{j}", "embedding": rng.normal(size=8).tolist()}
                          for j in range(5 + 3 * c)] for c in range(n_clusters)})
    return node


def _clusters(node_id: str, n: int, seed: int = 1) -> NodeClusters:
    return NodeClusters(node_id, list(range(n)), np.random.default_rng(seed).normal(size=(n, 8)), ["public"] * n)


# --- protocol -------------------------------------------------------------------


def test_every_node_gets_exactly_probes_points_whatever_the_question():
    nodes = [_clusters(n, 5, seed=i) for i, n in enumerate("abcd")]
    rng = np.random.default_rng(7)
    for _ in range(20):
        plan = plan_probes(rng.normal(size=8), nodes, probes=3)
        assert {n: len(p) for n, p in plan.points.items()} == {"a": 3, "b": 3, "c": 3, "d": 3}
        assert sum(len(r) for r in plan.real.values()) == 3          # the global top-3, wherever they are
        assert all(len(p) == POINT_BYTES for pts in plan.points.values() for p in pts)


def test_dummy_points_are_valid_group_elements_like_real_ones():
    """A node's only check (evaluate_for) accepts dummies exactly as real
    points; both are uniform in the prime-order group. A byte-level sanity
    check, not a proof — the argument is in docs/47."""
    node = _psi_node("n")
    plan = plan_probes(np.ones(8), [_clusters("n", 5)], probes=5)
    dummies = [dummy_point() for _ in range(5)]
    assert all(sodium.crypto_core_ed25519_is_valid_point(p) for p in dummies + plan.points["n"])
    assert len(node.evaluate_for(dummies, ["public"])) == 5
    real_bits = Counter(b & 1 for _ in range(300) for b in plan_probes(np.random.default_rng().normal(size=8),
                                                                       [_clusters("n", 5)], 1).points["n"][0][:16])
    dummy_bits = Counter(b & 1 for _ in range(300) for b in dummy_point()[:16])
    assert abs(real_bits[1] / sum(real_bits.values()) - 0.5) < 0.05
    assert abs(dummy_bits[1] / sum(dummy_bits.values()) - 0.5) < 0.05


def test_unlock_opens_exactly_the_chosen_clusters_by_lookup():
    nodes = {n: _psi_node(n, seed=i) for i, n in enumerate("abc")}
    cache = TableCache()
    for n, node in nodes.items():
        cache.put(n, node.blind_table())
    plan = plan_probes(np.random.default_rng(3).normal(size=8), [_clusters(n, 5, seed=i) for i, n in enumerate("abc")],
                       probes=4)
    opened = {n: unlock(plan, n, nodes[n].evaluate_for(plan.points[n], ["public"]), cache) for n in nodes}
    assert {(n, c) for n, got in opened.items() for c in got} == {(n, c) for n, c, _ in plan.chosen}
    for n, got in opened.items():
        for cid, passages in got.items():
            assert [p["document"] for p in passages] == [p["document"] for p in nodes[n]._clusters[cid]]


def test_table_is_padded_deterministic_and_role_scoped():
    node = PSINode("h")
    rng = np.random.default_rng(0)
    node.build_table({0: [{"document": "a", "embedding": [0.1] * 4}],
                      1: [{"document": "b" * 500, "embedding": rng.normal(size=4).tolist()}] * 7,
                      2: [{"document": "note", "embedding": [0.2] * 4}]},
                     {0: "public", 1: "public", 2: "clinical_notes"})
    public = node.blind_table()
    both = node.blind_table(["public", "clinical_notes"])
    assert len(public["entries"]) == 2 and len(both["entries"]) == 3       # restricted size hidden from outsiders
    assert len({len(e) for e in both["entries"].values()}) == 1            # one envelope length
    node._blind = None
    assert node.blind_table()["version"] == public["version"]              # byte-identical rebuild


def test_compact_payload_round_trips():
    passages = [{"document": "x", "embedding": [0.5, -0.25], "collection": "research"}]
    back = decode_passages(encode_passages(passages) + b"\0" * 40)
    assert back[0]["document"] == "x" and back[0]["collection"] == "research"
    assert np.allclose(back[0]["embedding"], [0.5, -0.25])


def test_rotated_keys_lock_out_the_cached_table():
    node = _psi_node("n")
    cache = TableCache()
    cache.put("n", node.blind_table())
    old_epoch = node.epoch
    node.rotate_keys()
    assert node.epoch != old_epoch and not cache.is_current("n", node.epoch)
    plan = plan_probes(np.ones(8), [_clusters("n", 5)], probes=2)
    assert unlock(plan, "n", node.evaluate_for(plan.points["n"], ["public"]), cache) == {}   # old copy: opaque
    cache.put("n", node.blind_table())
    assert len(unlock(plan, "n", node.evaluate_for(plan.points["n"], ["public"]), cache)) == 2


# --- through AppState -------------------------------------------------------------


def _docs(topic: int, n: int = 40) -> list[str]:
    return [f"topic{topic} passage {j} about subject {topic} detail {j % 7}" for j in range(n)]


def _state(tmp_path: Path, n_nodes: int = 6) -> AppState:
    state = AppState(instrumentation_path=str(tmp_path / "q.jsonl"))
    state.generator = None
    for i in range(n_nodes):
        state.register_node(node_id=f"n{i}", documents=_docs(i), policy_labels=[], k=2, sigma=0.0)
    return state


def test_blind_mode_contacts_every_node_equally_and_never_sends_the_query(tmp_path, monkeypatch):
    state = _state(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("node received the query")

    monkeypatch.setattr(InProcessNode, "retrieve", forbidden)
    monkeypatch.setattr(InProcessNode, "retrieve_from_text", forbidden)
    monkeypatch.setattr(InProcessNode, "retrieve_vector", forbidden)
    seen = []
    for question in ("topic2 subject 2", "topic5 subject 5 detail 3"):
        r = state.run_query(question, max_nodes=3, genuine_k=1, sigma=0.0, routing_mode="blind", blind_probes=3)
        assert r["nodes_contacted"] == [f"n{i}" for i in range(6)]
        per = r["routing_details"]["blind"]["per_node"]
        seen.append({n: v["probes_sent"] for n, v in per.items()})
        assert r["citations"]
    assert seen[0] == seen[1] == {f"n{i}": 3 for i in range(6)}             # identical traffic for both questions
    assert "topic5" in r["citations"][0]["document"]


def test_tables_download_once_and_again_only_on_key_rotation(tmp_path):
    state = _state(tmp_path, n_nodes=3)
    first = state.run_query("topic1 subject 1", max_nodes=2, genuine_k=1, sigma=0.0, routing_mode="blind")
    second = state.run_query("topic2 subject 2", max_nodes=2, genuine_k=1, sigma=0.0, routing_mode="blind")
    assert first["routing_details"]["blind"]["table_downloads_this_query"] == 3
    assert second["routing_details"]["blind"]["table_downloads_this_query"] == 0
    state.nodes["n1"].psi.rotate_keys()
    third = state.run_query("topic0 subject 0", max_nodes=2, genuine_k=1, sigma=0.0, routing_mode="blind")
    assert third["routing_details"]["blind"]["table_downloads_this_query"] == 1
    assert third["citations"]


def test_budget_is_charged_for_dummies_too(tmp_path):
    state = _state(tmp_path, n_nodes=3)
    cred = new_credential("c")
    for i in range(3):
        state.nodes[f"n{i}"].authorizer = Authorizer(f"n{i}", {"c": ClientPolicy(cred.key, 100)})
    state.credential = cred
    state.run_query("topic1 subject 1", max_nodes=2, genuine_k=1, sigma=0.0, routing_mode="blind", blind_probes=4)
    used = {n: state.nodes[n].authorizer.usage for n in ("n0", "n1", "n2")}
    assert all(sum(u.values()) == 4 for u in used.values())               # real or dummy, the node counts 4


def test_request_schema_accepts_blind_and_rejects_sigma():
    assert QueryRequest(question="q", routing_mode="blind", blind_probes=6).blind_probes == 6
    with pytest.raises(ValueError):
        QueryRequest(question="q", routing_mode="blind", sigma=0.1)


# --- real MCP node -----------------------------------------------------------------


@pytest.fixture
def mcp_nodes(tmp_path: Path) -> list[Path]:
    files = []
    for i in range(2):
        data = tmp_path / f"m{i}.json"
        data.write_text(json.dumps({"node_id": f"m{i}", "local_model": "toy-e5", "documents": _docs(i)}))
        files.append(data)
    return files


def test_blind_mode_over_real_mcp(mcp_nodes, tmp_path, monkeypatch):
    state = AppState(instrumentation_path=str(tmp_path / "q.jsonl"))
    state.generator = None
    for f in mcp_nodes:
        asyncio.run(state.register_mcp_node_async(f))

    def forbidden(*args, **kwargs):
        raise AssertionError("text or vector retrieval called")

    monkeypatch.setattr(MCPNodeHandle, "retrieve_from_text", forbidden)
    monkeypatch.setattr(MCPNodeHandle, "retrieve_vector", forbidden)
    r = state.run_query("topic1 subject 1", max_nodes=2, genuine_k=1, sigma=0.0, routing_mode="blind", blind_probes=2)
    assert r["routing_details"]["blind"]["errors"] == {}
    assert {v["probes_sent"] for v in r["routing_details"]["blind"]["per_node"].values()} == {2}
    assert r["citations"] and "topic1" in r["citations"][0]["document"]
    table = MCPNodeHandle("m0", mcp_nodes[0]).psi_table(None)
    again = MCPNodeHandle("m0", mcp_nodes[0]).psi_table(None)
    assert table["version"] == again["version"]                  # a fresh node process serves identical bytes


def test_every_node_is_contacted_before_anything_is_unlocked(tmp_path, monkeypatch):
    """docs/51: unlocking between contacts made inter-request gaps depend on
    which nodes held real probes — a timing channel. All sends come first."""
    import privacy.blind_unlock as shared
    from privacy.psi import PSINode

    state = _state(tmp_path, n_nodes=4)
    events = []
    original_eval, original_unlock = PSINode.evaluate_for, shared.unlock
    monkeypatch.setattr(PSINode, "evaluate_for", lambda self, *a, **k: events.append("send") or original_eval(self, *a, **k))
    monkeypatch.setattr(shared, "unlock", lambda *a, **k: events.append("unlock") or original_unlock(*a, **k))
    state.run_query("topic1 subject 1", max_nodes=2, genuine_k=1, sigma=0.0, routing_mode="blind", blind_probes=3)
    assert events[:4] == ["send"] * 4 and set(events[4:]) <= {"unlock"}   # unlock only nodes with real probes


# --- chunked, compressed tables (docs/47 addendum) -----------------------------


def _big_node(dtype: str = "float16") -> PSINode:
    rng = np.random.default_rng(5)
    node = PSINode("big")
    node.blind_embedding_dtype = dtype
    node.build_table({c: [{"document": " ".join(rng.choice(["fever", "rash", "cough", "troponin", "ecg"], 400)),
                           "embedding": rng.normal(size=768).tolist()} for _ in range(4 + 12 * c)] for c in range(3)})
    return node


def test_large_clusters_span_several_equal_chunks_and_still_open():
    from privacy.psi import CHUNK_BYTES

    node = _big_node()
    table = node.blind_table()
    lengths = {len(e) for e in table["entries"].values()}
    assert lengths == {CHUNK_BYTES + 24 + 16}                          # every envelope identical in size
    assert len(table["entries"]) > len(node._clusters)                 # the big cluster needed several chunks
    cache = TableCache()
    cache.put("big", table)
    plan = plan_probes(np.ones(8), [_clusters("big", 3)], probes=3)
    opened = unlock(plan, "big", node.evaluate_for(plan.points["big"], ["public"]), cache)
    assert {c: len(v) for c, v in opened.items()} == {c: len(node._clusters[c]) for c in range(3)}


def test_a_tampered_chunk_makes_its_cluster_unopenable():
    node = _big_node()
    table = node.blind_table()
    tag = next(iter(table["entries"]))
    table["entries"][tag] = table["entries"][tag][:-1] + bytes([table["entries"][tag][-1] ^ 1])
    cache = TableCache()
    cache.put("big", table)
    plan = plan_probes(np.ones(8), [_clusters("big", 3)], probes=3)
    assert len(unlock(plan, "big", node.evaluate_for(plan.points["big"], ["public"]), cache)) == 2


def test_int8_embeddings_halve_the_vectors_and_keep_the_ranking():
    rng = np.random.default_rng(0)
    passages = [{"document": f"d{i}", "embedding": (v / np.linalg.norm(v)).tolist()}
                for i, v in enumerate(rng.normal(size=(50, 768)))]
    back = decode_passages(encode_passages(passages, "int8"))
    q = rng.normal(size=768)
    exact = np.argsort(-np.array([p["embedding"] for p in passages]) @ q)[:10]
    approx = np.argsort(-np.array([p["embedding"] for p in back]) @ q)[:10]
    assert len(encode_passages(passages, "int8")) < 0.6 * len(encode_passages(passages, "float16"))
    assert len(set(exact) & set(approx)) >= 9


def test_chunked_table_is_several_times_smaller_than_padding_to_the_largest_cluster():
    node = _big_node()
    chunked = sum(len(e) for e in node.blind_table()["entries"].values())
    widest = max(len(encode_passages(p)) for p in node._clusters.values())
    assert chunked < 0.5 * widest * len(node._clusters)
