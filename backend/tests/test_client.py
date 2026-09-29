"""Standalone device client and cover traffic (client/, docs/52).

Checks the stated properties at the interface on synthetic data: no server
in the path and no node tool that takes text or a vector is ever called;
planning touches no network; a cover round is the same on the wire as a real
one; the scheduler sends exactly one round per tick; roles and the fail-
closed signature check hold through the client. Not privacy measurements.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from api.state import AppState
from client import CoverTrafficScheduler, Device, LocalTransport, MCPTransport
from nodes.mcp_client import MCPNodeHandle
from nodes.simulator import InProcessNode
from privacy.credentials import Authorizer, ClientPolicy, new_credential


def _docs(topic: int, n: int = 40) -> list[str]:
    return [f"topic{topic} passage {j} about subject {topic} detail {j % 7}" for j in range(n)]


def _simulated(tmp_path: Path, n: int = 4) -> AppState:
    state = AppState(instrumentation_path=str(tmp_path / "q.jsonl"))
    state.generator = None
    for i in range(n):
        state.register_node(node_id=f"n{i}", documents=_docs(i), policy_labels=[], k=2, sigma=0.0)
    return state


def _device(state: AppState, **kw) -> Device:
    device = Device(embedder=state.routing_embedder, **kw)
    for node_id in sorted(state.nodes):
        device.connect(LocalTransport(state.nodes[node_id], state.registry.get(node_id)))
    return device


@pytest.fixture
def forbid_query_tools(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("a node received the question")

    for name in ("retrieve", "retrieve_from_text", "retrieve_vector"):
        monkeypatch.setattr(InProcessNode, name, forbidden)
    monkeypatch.setattr(MCPNodeHandle, "retrieve_from_text", forbidden)
    monkeypatch.setattr(MCPNodeHandle, "retrieve_vector", forbidden)


def test_device_answers_with_every_node_receiving_the_same_points(tmp_path, forbid_query_tools):
    device = _device(_simulated(tmp_path), probes=3)
    result = device.ask("topic2 subject 2")
    assert {n: s["points"] for n, s in result["sent"].items()} == {f"n{i}": 3 for i in range(4)}
    assert result["citations"] and "topic2" in result["citations"][0]["document"]
    assert sum(result["real_probes"].values()) == 3


def test_planning_touches_no_network(tmp_path, monkeypatch):
    device = _device(_simulated(tmp_path))

    def network(*args, **kwargs):
        raise AssertionError("planning contacted a node")

    for t in device.transports.values():
        monkeypatch.setattr(t, "evaluate", network)
        monkeypatch.setattr(t, "table", network)
        monkeypatch.setattr(t, "restricted", network)
    device.plan("topic1 subject 1")


def test_a_cover_round_looks_like_a_real_round_on_the_wire(tmp_path):
    state = _simulated(tmp_path)
    cred = new_credential("c")
    for i in range(4):
        state.nodes[f"n{i}"].authorizer = Authorizer(f"n{i}", {"c": ClientPolicy(cred.key, 1000)})
    device = _device(state, credential=cred, probes=4)
    real = device.ask("topic1 subject 1")["sent"]
    cover = device.cover()["sent"]
    assert {n: (s["points"], s["request_bytes"]) for n, s in real.items()} == \
           {n: (s["points"], s["request_bytes"]) for n, s in cover.items()}
    assert {n: sum(state.nodes[n].authorizer.usage.values()) for n in real} == {n: 8 for n in real}   # 4 + 4 each


def test_scheduler_sends_exactly_one_round_per_tick(tmp_path):
    device = _device(_simulated(tmp_path), probes=2)
    calls = []
    original = device.send
    device.send = lambda plan: calls.append(len(plan.points)) or original(plan)
    scheduler = CoverTrafficScheduler(device, interval_s=0)
    assert scheduler.tick() is None                      # nothing asked: cover
    ticket = scheduler.submit("topic3 subject 3")
    assert calls == [4]                                  # submitting sends nothing
    answered = scheduler.tick()
    assert answered is ticket and "topic3" in ticket.result["citations"][0]["document"]
    scheduler.tick()
    assert scheduler.rounds == ["cover", "real", "cover"] and calls == [4, 4, 4]


def test_timed_run_does_not_let_generation_delay_later_rounds(monkeypatch):
    import client.cover as cover_module

    clock = [0.0]
    monkeypatch.setattr(cover_module, "time", SimpleNamespace(
        time=lambda: clock[0], monotonic=lambda: clock[0],
        sleep=lambda seconds: clock.__setitem__(0, clock[0] + seconds)))
    sent_at = []

    class SlowGeneratorDevice:
        def plan(self, question):
            return question, question

        def refresh(self):
            pass

        def send(self, plan):
            sent_at.append(clock[0])
            return plan

        def cover(self):
            sent_at.append(clock[0])

        def finish(self, question, q, plan, result):
            clock[0] += 20.0
            return {"answer": question}

    scheduler = CoverTrafficScheduler(SlowGeneratorDevice(), interval_s=5.0)
    ticket = scheduler.submit("private question")
    assert scheduler.run(3, first_real_at=1) == [ticket]
    assert sent_at == [0.0, 5.0, 10.0]
    assert scheduler.rounds == ["cover", "real", "cover"]
    assert ticket.result == {"answer": "private question"}


def test_roles_hold_through_the_client(tmp_path):
    """A clinician unlocks clinical notes; a researcher never does, whatever it asks."""
    from api.demo import build_demo_federation

    state = AppState(instrumentation_path=str(tmp_path / "q.jsonl"))
    state.generator = None
    build_demo_federation(state)
    unlocked = {}
    for who in ("demo-researcher", "demo-clinician"):
        device = _device(state, credential=state.demo_identities[who], probes=12)
        _, plan = device.plan("clinical note patient admitted with chest pain troponin")
        result = device.send(plan)
        assert result.errors == {}
        unlocked[who] = {p.get("collection") for opened in result.opened.values() for ps in opened.values() for p in ps}
    assert "clinical_notes" in unlocked["demo-clinician"]
    assert "clinical_notes" not in unlocked["demo-researcher"]


def test_unsigned_restricted_centroids_are_refused(tmp_path):
    from api.demo import build_demo_federation

    state = AppState(instrumentation_path=str(tmp_path / "q.jsonl"))
    state.generator = None
    build_demo_federation(state)
    node_id = "st_marys_cardiology"
    profile = state.registry.get(node_id)
    profile.public_key = profile.public_key or b"\x01" * 32   # the node claims to sign

    class Unsigned(LocalTransport):
        def restricted(self, auth):
            return {**super().restricted(auth), "signature": None}

    device = Device(embedder=state.routing_embedder, credential=state.demo_identities["demo-clinician"])
    with pytest.raises((PermissionError, ValueError)):
        device.connect(Unsigned(state.nodes[node_id], profile))


def test_device_over_real_mcp_nodes_with_no_server(tmp_path, forbid_query_tools):
    files = []
    for i in range(2):
        data = tmp_path / f"m{i}.json"
        data.write_text(json.dumps({"node_id": f"m{i}", "local_model": "toy-e5", "documents": _docs(i)}))
        files.append(data)
    from nodes.embedding import shared_routing_embedder

    device = Device(embedder=shared_routing_embedder(), probes=2)
    for f in files:
        device.connect(MCPTransport(MCPNodeHandle(f.stem, f)))
    result = device.ask("topic1 subject 1")
    assert result["errors"] == {} and "topic1" in result["citations"][0]["document"]
    assert {s["points"] for s in result["sent"].values()} == {2}
