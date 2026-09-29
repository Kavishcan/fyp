"""The user's device: blind unlock with no server in the path (docs/52).

In the API/studio the coordinator process plays the device (docs/41), so
"the API process sees the question" was a standing caveat. `Device` is the
same protocol as a standalone library the user runs: it embeds the question,
plans the probes, talks to each node through a NodeTransport, unlocks,
ranks and (optionally) generates locally. No component other than this
object ever holds the question. What leaves it per round is recorded in the
returned `sent` field — blinded points and a credential, per node.

    device = Device(credential=cred)
    for t in transports: device.connect(t)
    result = device.ask("58-year-old with ...")

`cover()` sends a round with no real probe (docs/52: constant-rate cover
traffic, client/cover.py).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from privacy.blind_unlock import NodeClusters, TableCache, blind_round, cover_plan, plan_probes
from router.hybrid_rerank import DEFAULT_WEIGHT, hybrid_scores
from router.registry import SourceRegistry


@dataclass
class Device:
    embedder: object = None
    credential: object = None
    generator: object = None
    probes: int = 8
    rerank_weight: float = DEFAULT_WEIGHT     # 0 = dense only (docs/48)
    evidence_top_k: int = 2
    cache: TableCache = field(default_factory=TableCache)
    registry: SourceRegistry = field(default_factory=SourceRegistry)
    transports: dict = field(default_factory=dict)
    _restricted: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.embedder is None:
            from nodes.embedding import shared_routing_embedder

            self.embedder = shared_routing_embedder()

    # --- setup -------------------------------------------------------------------

    def connect(self, transport) -> None:
        """Fetch and verify the node's signed profile (a present-but-invalid
        signature is refused by the registry), check it is in this device's
        routing space, and download its table once."""
        profile = transport.profile()
        expected = np.asarray(self.embedder.embed(["dimension probe"])).shape[1]
        got = np.asarray(profile.centroids).shape[-1]
        if got != expected:
            raise ValueError(f"node {profile.source_id!r} publishes {got}-d centroids; this device embeds in {expected}-d")
        self.registry.publish(profile)
        self.transports[profile.source_id] = transport
        self.cache.put(profile.source_id, transport.table(self._auth(profile.source_id)))
        self.refresh()

    def refresh(self) -> None:
        """Fetch the day's restricted centroids for every node — at connect
        time and on the scheduler's tick, never when a question is typed, so
        no request is timed by a question (docs/52)."""
        from privacy.credentials import utc_day

        if self.credential is None:
            return
        for node_id in sorted(self.transports):
            profile = self.registry.get(node_id)
            if not profile.access_policy or self._restricted.get(node_id, (None,))[0] == utc_day():
                continue
            reply = self.transports[node_id].restricted(self._auth(node_id))
            if profile.public_key:
                from nodes.signing import verify_payload

                payload = {k: reply[k] for k in ("node_id", "client_id", "day", "clusters") if k in reply}
                if not reply.get("signature") or not verify_payload(profile.public_key, payload, reply["signature"]):
                    raise PermissionError(f"node {node_id!r}: restricted centroids failed signature check")
            self._restricted[node_id] = (utc_day(), reply.get("clusters", []))

    def _auth(self, node_id: str, points: list[bytes] | None = None) -> dict | None:
        return self.credential.sign(node_id, points or []) if self.credential is not None else None

    def _clusters(self, node_id: str) -> NodeClusters:
        """Public clusters from the signed profile plus the restricted ones
        fetched by refresh() (verified there, fail closed). Uses what is
        cached, even from an earlier day: planning never touches the network."""
        from privacy.credentials import permitted_collections

        profile = self.registry.get(node_id)
        pub = profile.cluster_centroids
        ids = list(range(0 if pub is None else len(pub)))
        cents = [] if pub is None else [np.asarray(v, dtype=np.float64) for v in np.asarray(pub)]
        colls = list(profile.cluster_collections or ["public"] * len(ids))
        if self.credential is not None and profile.access_policy:
            for e in self._restricted.get(node_id, (None, []))[1]:
                ids.append(int(e["id"]))
                cents.append(np.asarray(e["centroid"], dtype=np.float64))
                colls.append(e["collection"])
        roles = self.credential.roles if self.credential is not None else ()
        readable = set(permitted_collections(profile.access_policy, roles, sorted(set(colls)),
                                             authorised=self.credential is not None))
        keep = [i for i, c in enumerate(colls) if c in readable]
        return NodeClusters(node_id, [ids[i] for i in keep],
                            np.asarray([cents[i] for i in keep]) if keep else np.empty((0, 0)),
                            [colls[i] for i in keep])

    # --- questions -----------------------------------------------------------------

    def plan(self, question: str):
        """Everything question-dependent that happens before sending: local."""
        q = np.asarray(self.embedder.embed([question])[0], dtype=np.float64)
        nodes = [self._clusters(n) for n in sorted(self.transports)]
        return q, plan_probes(q, nodes, self.probes)

    def send(self, plan):
        return blind_round(plan, self.transports, self.cache, self.credential)

    def ask(self, question: str) -> dict:
        started = time.perf_counter()
        q, plan = self.plan(question)
        result = self.send(plan)
        return self.finish(question, q, plan, result, started)

    def finish(self, question: str, q: np.ndarray, plan, result, started: float | None = None) -> dict:
        """Local after the round: rank the unlocked passages, keep the top
        evidence, generate if a local generator is configured."""
        pool = [dict(p, node_id=n) for n, opened in result.opened.items() for cid in sorted(opened) for p in opened[cid]]
        if pool:
            scores = hybrid_scores(question, q, [p["document"] for p in pool],
                                   np.asarray([p["embedding"] for p in pool]), self.rerank_weight)
            ranked = [pool[i] for i in np.argsort(-scores)]
        else:
            ranked = []
        evidence = ranked[: self.evidence_top_k]
        answer = self.generator.generate(question, [p["document"] for p in evidence]) if self.generator and evidence else None
        return {
            "answer": answer,
            "citations": [{"node_id": p["node_id"], "document": p["document"], "collection": p.get("collection")}
                          for p in evidence],
            "passages_unlocked": len(pool),
            "sent": {n: {"points": len(plan.points[n]), "request_bytes": result.request_bytes.get(n),
                         "response_bytes": result.response_bytes.get(n)} for n in sorted(plan.points)},
            "real_probes": {n: len(r) for n, r in plan.real.items()},     # device-only knowledge
            "errors": result.errors,
            "table_downloads": result.downloads,
            "ms": None if started is None else (time.perf_counter() - started) * 1000.0,
        }

    def cover(self) -> dict:
        """A round with no real probe: same nodes, order and counts as ask()."""
        result = self.send(cover_plan(list(self.transports), self.probes))
        return {"sent": {n: {"points": self.probes, "request_bytes": result.request_bytes.get(n)} for n in sorted(self.transports)},
                "errors": result.errors, "table_downloads": result.downloads}
