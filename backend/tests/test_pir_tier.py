"""Tier 2 of blind unlock: PIR fetch instead of full table download (docs/55).

Checks retrieval correctness and that the PIR path opens exactly what the
full-download path opens, with a fixed number of queries per node. Not a
security proof of the PIR scheme (parameters are SimplePIR's).
"""
from __future__ import annotations

import os

import numpy as np
import pytest

from privacy.blind_unlock import NodeClusters, TableCache, plan_probes, pir_unlock, unlock
from privacy.pir import PIRClient, PIRServer, pack
from privacy.psi import PSINode


def test_pir_returns_the_asked_record_from_any_slot():
    rng = np.random.default_rng(0)
    groups = [[(os.urandom(16), os.urandom(300)) for _ in range(int(rng.integers(1, 5)))] for _ in range(80)]
    D, layout = pack(groups, 300, per_column=3)
    server = PIRServer(D)
    client = PIRClient(server.seed, server.hint(), layout)
    for group in groups[::7]:
        for tag, record in group:
            col, slot = layout.position[tag]
            assert client.record(client.fetch([col], server.answer)[col], slot) == record


def test_pack_keeps_small_groups_in_one_column_and_hides_nothing_in_order():
    groups = [[(bytes([g, i]) * 8, bytes(10)) for i in range(n)] for g, n in enumerate([1, 2, 3, 2, 1])]
    _, layout = pack(groups, 10, per_column=4)
    for g, n in enumerate([1, 2, 3, 2, 1]):
        cols = {layout.position[bytes([g, i]) * 8][0] for i in range(n)}
        assert len(cols) == 1
    assert list(layout.position) == sorted(layout.position)          # the map is sorted by tag, not by cluster


def _node(node_id, seed):
    rng = np.random.default_rng(seed)
    node = PSINode(node_id)
    node.build_table({c: [{"document": f"{node_id}-{c}-{j}", "embedding": rng.normal(size=8).tolist()}
                          for j in range(5 + 3 * c)] for c in range(6)})
    return node


def test_pir_unlock_opens_what_the_full_download_opens_with_fixed_queries():
    nodes = {n: _node(n, i) for i, n in enumerate("abc")}
    clusters = [NodeClusters(n, list(range(6)), np.random.default_rng(10 + i).normal(size=(6, 8)), ["public"] * 6)
                for i, n in enumerate("abc")]
    cache = TableCache()
    pir = {}
    for n, node in nodes.items():
        cache.put(n, node.blind_table())
        server, layout = node.pir_database(per_column=2)
        pir[n] = (server, PIRClient(server.seed, server.hint(), layout))
    for trial in range(4):
        plan = plan_probes(np.random.default_rng(trial).normal(size=8), clusters, probes=3)
        sent = {}
        for n, node in nodes.items():
            evaluated = node.evaluate_for(plan.points[n], ["public"])
            server, client = pir[n]
            calls = []

            def answer(q, server=server, calls=calls):
                calls.append(q.shape)
                return server.answer(q)

            got, stats = pir_unlock(plan, n, evaluated, client, answer, columns=3)
            assert got == unlock(plan, n, evaluated, cache)
            assert stats["clusters_truncated"] == 0
            sent[n] = calls
        assert {n: c for n, c in sent.items()} == {n: [(3, pir[n][1].layout.cols)] for n in nodes}


def test_pir_rejects_a_wrong_length_query():
    D, layout = pack([[(b"t" * 16, bytes(8))]], 8, 1)
    with pytest.raises(ValueError):
        PIRServer(D).answer(np.zeros((1, layout.cols + 1), dtype=np.uint32))


def test_tier_rule_keeps_small_hospitals_on_download_and_moves_large_ones_to_pir():
    from privacy.pir import recommended_tier

    record = 16424
    assert recommended_tier(15_000_000, 15_000_000 // record, record) == "download"        # PMC-sized hospital
    assert recommended_tier(110 * 10**9, 110 * 10**9 // record, record, per_column=16) == "pir"   # 100 GB of text
