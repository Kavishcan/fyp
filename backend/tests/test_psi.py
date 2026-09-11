"""Labeled-PSI dispatch (privacy/psi.py). These check the protocol's
functional and hiding properties on toy data; they are not a security proof
and say nothing about retrieval quality."""
from __future__ import annotations

import json

import pytest

from privacy.psi import (
    BlindedQuery,
    PSIClient,
    PSINode,
    encode_cluster_id,
    hash_to_point,
    label_key,
    open_envelope,
    random_scalar,
    scalar_invert,
    scalar_mult,
    seal,
)


def _node(n_clusters: int = 20) -> PSINode:
    node = PSINode("node-a")
    node.build_table({c: [{"document": f"cluster {c} passage {i}", "score": 0.5} for i in range(3)]
                      for c in range(n_clusters)})
    return node


def test_blind_evaluate_unblind_equals_direct_oprf():
    node = _node()
    q = PSIClient.blind([3, 7])
    outputs = PSIClient.unblind(q, node.evaluate(q.blinded))
    for cid, out in zip([3, 7], outputs):
        assert out == scalar_mult(node.key, hash_to_point(encode_cluster_id(cid)))


def test_client_recovers_exactly_the_queried_clusters_and_nothing_else():
    node = _node()
    q = PSIClient.blind([3, 7])
    outputs = PSIClient.unblind(q, node.evaluate(q.blinded))
    found = PSIClient.open_matches(q, outputs, node.node_id, node.envelopes_for(None))
    assert set(found) == {3, 7}
    assert found[3][0]["document"] == "cluster 3 passage 0"


def test_unqueried_envelopes_are_opaque():
    node = _node()
    q = PSIClient.blind([3])
    outputs = PSIClient.unblind(q, node.evaluate(q.blinded))
    key = label_key(outputs[0], node.node_id)
    with pytest.raises(Exception):
        open_envelope(key, node.table[4])


def test_blinded_points_differ_across_queries_for_the_same_id():
    """The node sees a fresh uniform point every time — no linkability."""
    a = PSIClient.blind([5]).blinded[0]
    b = PSIClient.blind([5]).blinded[0]
    assert a != b


def test_wrong_node_key_yields_no_matches():
    node = _node()
    other = PSINode("node-a", key=random_scalar())
    q = PSIClient.blind([3])
    outputs = PSIClient.unblind(q, other.evaluate(q.blinded))   # evaluated by the wrong key
    assert PSIClient.open_matches(q, outputs, node.node_id, node.envelopes_for(None)) == {}


def test_label_key_is_bound_to_node_id():
    """Two nodes sharing an OPRF key still get distinct envelope keys."""
    node_a = PSINode("node-a", key=random_scalar())
    node_b = PSINode("node-b", key=node_a.key)     # same OPRF key, different id
    node_b.build_table({1: [{"document": "b"}]})
    q = PSIClient.blind([1])
    outputs = PSIClient.unblind(q, node_a.evaluate(q.blinded))
    assert PSIClient.open_matches(q, outputs, "node-a", node_b.envelopes_for(None)) == {}
    assert set(PSIClient.open_matches(q, outputs, "node-b", node_b.envelopes_for(None))) == {1}


def test_fetch_set_limits_delivered_envelopes_but_not_matches():
    node = _node(50)
    q = PSIClient.blind([9])
    outputs = PSIClient.unblind(q, node.evaluate(q.blinded))
    delivered = node.envelopes_for([9, 10, 11, 12, 13])
    assert len(delivered) == 5
    found = PSIClient.open_matches(q, outputs, node.node_id, delivered)
    assert set(found) == {9}


def test_evaluate_rejects_invalid_points():
    node = _node()
    with pytest.raises(ValueError):
        node.evaluate([b"\x00" * 31])


def test_tokens_are_random_not_derived_from_cluster_ids():
    a = _node(5).tokens
    b = _node(5).tokens
    assert set(a.values()).isdisjoint(set(b.values()))


def test_seal_open_roundtrip_and_tamper_detection():
    key = label_key(random_scalar(), "n")
    env = seal(key, b"hello")
    assert open_envelope(key, env) == b"hello"
    tampered = env[:-1] + bytes([env[-1] ^ 1])
    with pytest.raises(Exception):
        open_envelope(key, tampered)


def test_scalar_inverse_roundtrip():
    r = random_scalar()
    p = hash_to_point(b"x")
    assert scalar_mult(scalar_invert(r), scalar_mult(r, p)) == p
