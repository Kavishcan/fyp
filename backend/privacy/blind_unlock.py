"""Blind unlock: download once, unlock blindly (docs/47).

Per-query labeled PSI (privacy/psi.py, docs/36) ships a node's whole
encrypted table on every contact, and only the contacted nodes see probes —
so it costs ~100 MB per question at PMC scale and the contact pattern still
names the topic unless cells or broadcast hide it (docs/39–40, docs/46).
Blind unlock separates the two jobs:

Offline, once per key epoch — every node publishes its whole cluster table
(PSINode.blind_table): envelopes padded to one length, each labelled by a
tag derived from the OPRF output instead of a random token. Every device of
a role downloads the same bytes, so the download reveals nothing about any
question.

Online, per question — the device ranks every published cluster of every
node locally, takes the best `probes` overall, and sends EXACTLY `probes`
blinded points to EVERY node: real points r·H(c) for its chosen clusters
there, fresh dummy points (privacy/psi.dummy_point) for the rest, in random
order, to nodes in a fixed (sorted) order. Real and dummy points have the
same distribution, so every node sees identical traffic on every question.
The device unblinds the real replies, derives tag and key, and opens its
envelope from the cache by lookup; dummy replies are discarded.

What a node learns per question: this credential sent `probes` points.
Not the question, not which clusters, not whether any point was real.
What an observer learns: every node was contacted with the same volume.
Budgets are charged per point, dummies included.

This composes known pieces: labeled PSI over an OPRF, offline/online split
(as in PIR hint schemes), and indistinguishable fake queries (as in Wally,
which needs a crowd of clients and an anonymity network; here one device
pads every node itself). Not measured: timing side channels, a malicious
node serving different tables to different clients (it gains no feedback
channel, but this is argued, not proven).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

import numpy as np
from nacl.exceptions import CryptoError

from privacy.psi import (decode_passages, dummy_point, encode_cluster_id, hash_to_point, label_key, label_tag,
                         open_envelope, random_scalar, scalar_invert, scalar_mult)


@dataclass
class NodeClusters:
    """What the device knows about one node's clusters: public ids and
    centroids from the signed profile, plus restricted ones fetched with the
    credential (docs/45). Only readable collections belong here."""
    node_id: str
    ids: list[int]
    centroids: np.ndarray
    collections: list[str]


@dataclass
class ProbePlan:
    """Per node, the points to send and (device-only) which ones are real."""
    points: dict[str, list[bytes]]
    real: dict[str, list[tuple[int, int, bytes]]]   # node -> [(position, cluster id, r)]
    chosen: list[tuple[str, int, float]]             # (node, cluster id, score), best first

    @property
    def genuine_nodes(self) -> list[str]:
        return sorted(n for n, r in self.real.items() if r)


def plan_probes(query_vector: np.ndarray, nodes: list[NodeClusters], probes: int,
                rng: random.Random | None = None) -> ProbePlan:
    """Global top-`probes` clusters across every node; then every node gets
    exactly `probes` points — its real ones plus dummies — in shuffled order.
    Padding every node to `probes` (not to its real count) is what makes the
    per-node volume independent of where the relevant clusters are."""
    if probes < 1:
        raise ValueError("probes must be positive")
    rng = rng or random.SystemRandom()
    q = np.asarray(query_vector, dtype=np.float64)
    q = q / (np.linalg.norm(q) or 1.0)
    scored: list[tuple[float, str, int]] = []
    for n in nodes:
        if len(n.ids) == 0:
            continue
        c = np.asarray(n.centroids, dtype=np.float64)
        s = (c @ q) / np.maximum(np.linalg.norm(c, axis=1), 1e-12)
        scored.extend((float(v), n.node_id, int(cid)) for v, cid in zip(s, n.ids))
    scored.sort(key=lambda x: (-x[0], x[1], x[2]))
    chosen = [(node, cid, score) for score, node, cid in scored[:probes]]

    points: dict[str, list[bytes]] = {}
    real: dict[str, list[tuple[int, int, bytes]]] = {}
    for n in sorted(nodes, key=lambda x: x.node_id):
        wanted = [cid for node, cid, _ in chosen if node == n.node_id]
        slots = [("real", cid) for cid in wanted] + [("dummy", None)] * (probes - len(wanted))
        rng.shuffle(slots)
        pts, reals = [], []
        for pos, (kind, cid) in enumerate(slots):
            if kind == "real":
                r = random_scalar()
                pts.append(scalar_mult(r, hash_to_point(encode_cluster_id(cid))))
                reals.append((pos, cid, r))
            else:
                pts.append(dummy_point())
        points[n.node_id], real[n.node_id] = pts, reals
    return ProbePlan(points=points, real=real, chosen=chosen)


@dataclass
class CachedTable:
    epoch: str
    version: str
    entries: dict[bytes, bytes]

    def size_bytes(self) -> int:
        return sum(len(t) + len(e) for t, e in self.entries.items())


@dataclass
class TableCache:
    """The device's copies of every node's blind table, refreshed only when a
    node's key epoch changes — never because of a particular question."""
    tables: dict[str, CachedTable] = field(default_factory=dict)
    downloads: int = 0
    downloaded_bytes: int = 0

    def put(self, node_id: str, table: dict) -> None:
        entry = CachedTable(epoch=table["epoch"], version=table["version"], entries=dict(table["entries"]))
        self.tables[node_id] = entry
        self.downloads += 1
        self.downloaded_bytes += entry.size_bytes()

    def is_current(self, node_id: str, epoch: str | None) -> bool:
        t = self.tables.get(node_id)
        return t is not None and (epoch is None or t.epoch == epoch)


def unlock(plan: ProbePlan, node_id: str, evaluated: list[dict[str, bytes]], cache: TableCache) -> dict[int, list[dict]]:
    """Open the envelopes of this node's REAL probes from the cached table.
    Each reply carries one evaluation per collection the node let this
    credential read; exactly one of them yields a tag that exists. Dummy
    replies are never touched. Returns cluster id -> passages."""
    if len(evaluated) != len(plan.points[node_id]):
        raise ValueError("evaluated points do not match the probes sent")
    table = cache.tables.get(node_id)
    if table is None:
        raise KeyError(f"no cached blind table for node {node_id!r}")
    found: dict[int, list[dict]] = {}
    for pos, cid, r in plan.real[node_id]:
        inverse = scalar_invert(r)
        for collection, point in evaluated[pos].items():
            out = scalar_mult(inverse, point)
            envelope = table.entries.get(label_tag(out, node_id, collection))
            if envelope is None:
                continue
            try:
                found[cid] = decode_passages(open_envelope(label_key(out, node_id, collection), envelope))
            except CryptoError:   # tampered entry: treated as absent
                continue
            break
    return found
