"""In-process source simulation for scaling beyond real MCP transport.

docs/03-architecture.md: real MCP servers demonstrate the architecture over an
actual protocol at 8-16 sources; this module provides the same retrieval
behaviour without network transport for the 100/300/1000-source scaling study.
The split must be stated explicitly wherever results are reported — this
module is the simulated half, not a substitute claimed to be "live."

Two embedders, deliberately kept separate:

- `routing_embedder`: ONE shared model, the same for every node. Used only to
  build the published profile centroids. The router only ever compares things
  embedded with this model, so routing math stays valid regardless of how many
  distinct local models exist across nodes.
- `local_embedder`: a node's own choice, free to differ node to node. Used
  only for that node's local document index and for re-embedding the query at
  retrieval time. Never leaves this object, never compared against anything
  from another node or against the routing embedder's space.

Comparing a vector from one embedder against a vector from another is not
just lower-quality, it's not a valid operation — different models produce
unrelated, often differently-sized spaces. That's why retrieval always
re-embeds the raw query text through the node's own local_embedder rather than
reusing the routing-embedder vector the router used to select this node.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from baselines.base import SourceProfile
from nodes.profile import build_profile, embed_documents
from nodes.metadata import attach_metadata


@dataclass
class RetrievedPassage:
    source_id: str
    document: str
    score: float


class InProcessNode:
    """Holds one source's local documents and answers `retrieve` locally.

    Documents never leave this object except as the text of the top-n
    passages returned by `retrieve` — the same boundary a real MCP node
    enforces, just without the network hop.
    """

    def __init__(
        self,
        source_id: str,
        documents: list[str],
        document_embeddings: np.ndarray,
        local_embedder: Callable[[list[str]], np.ndarray] | None = None,
        routing_embeddings: np.ndarray | None = None,
    ) -> None:
        if len(documents) != len(document_embeddings):
            raise ValueError("documents and document_embeddings must be the same length")
        self.source_id = source_id
        self.documents = documents
        self.document_embeddings = np.asarray(document_embeddings, dtype=np.float64)
        # Kept so retrieve_from_text can re-embed a raw query in this node's
        # own space; optional so existing vector-based callers/tests still work.
        self.local_embedder = local_embedder
        # PSI dispatch (privacy/psi.py): set by attach_psi_index. The node
        # answers OPRF evaluations and serves envelopes; it never sees a query.
        self.psi = None
        self.authorizer = None   # privacy/credentials.Authorizer when the node gates PSI
        # Role-based access (docs/45): collection label per document and the
        # node's role -> collections policy. The unauthenticated legacy/v2
        # retrieve paths can only ever return "public" documents.
        self.collections: list[str] = ["public"] * len(documents)
        self.access_policy: dict[str, list[str]] = {}
        self.restricted_clusters: dict[int, tuple[str, np.ndarray]] = {}   # id -> (collection, centroid)
        self.signing_key = None
        self.deid_counts: dict[str, int] | None = None   # identifiers redacted at load (docs/44)
        # v2 (docs/30): a second index in the SHARED routing space so the
        # coordinator can dispatch a vector instead of raw query text. Costs the
        # node retrieval-model heterogeneity for that mode — the shared encoder,
        # not the node's own local model, does v2 retrieval.
        if routing_embeddings is not None and len(routing_embeddings) != len(documents):
            raise ValueError("documents and routing_embeddings must be the same length")
        self.routing_embeddings = None if routing_embeddings is None else np.asarray(routing_embeddings, dtype=np.float64)

    def restricted_centroids(self, collections: list[str]) -> list[dict]:
        """Centroids of restricted clusters in `collections` — the caller has
        already been authorised and its permitted set computed (docs/45)."""
        wanted = set(collections)
        return [{"id": cid, "collection": c, "centroid": [float(x) for x in v]}
                for cid, (c, v) in sorted(self.restricted_clusters.items()) if c in wanted]

    def _public_only(self, scores: np.ndarray) -> np.ndarray:
        """The unauthenticated retrieve paths never rank a restricted document."""
        if all(c == "public" for c in self.collections):
            return scores
        mask = np.array([c == "public" for c in self.collections])
        return np.where(mask, scores, -np.inf)

    def retrieve_vector(self, routing_vector: np.ndarray, top_n: int = 5) -> list[RetrievedPassage]:
        """v2 dispatch: `routing_vector` is in the shared routing space, never
        raw text. Not query secrecy — a routing-space vector can still be
        inverted toward the query (attacks/a1_inversion.py); it removes the
        plaintext, nothing more.
        """
        if self.routing_embeddings is None:
            raise ValueError(f"node {self.source_id!r} has no routing-space index; build it with routing_embeddings")
        if not len(self.documents):
            return []
        q = np.asarray(routing_vector, dtype=np.float64)
        q_norm = np.linalg.norm(q) or 1.0
        doc_norms = np.linalg.norm(self.routing_embeddings, axis=1)
        doc_norms = np.where(doc_norms == 0, 1.0, doc_norms)
        scores = self._public_only((self.routing_embeddings @ q) / (doc_norms * q_norm))
        order = [i for i in np.argsort(scores)[::-1][:top_n] if np.isfinite(scores[i])]
        return [
            RetrievedPassage(source_id=self.source_id, document=self.documents[i], score=float(scores[i]))
            for i in order
        ]

    def retrieve(self, query_embedding: np.ndarray, top_n: int = 5) -> list[RetrievedPassage]:
        """Vector-in retrieval. `query_embedding` MUST already be in this
        node's own local embedding space — never pass a routing-embedder
        vector here, it will produce meaningless scores rather than an error.
        Prefer `retrieve_from_text` unless you already have the right vector.
        """
        if not len(self.documents):
            return []
        q = np.asarray(query_embedding, dtype=np.float64)
        q_norm = np.linalg.norm(q) or 1.0
        doc_norms = np.linalg.norm(self.document_embeddings, axis=1)
        doc_norms = np.where(doc_norms == 0, 1.0, doc_norms)
        scores = self._public_only((self.document_embeddings @ q) / (doc_norms * q_norm))
        order = [i for i in np.argsort(scores)[::-1][:top_n] if np.isfinite(scores[i])]
        return [
            RetrievedPassage(source_id=self.source_id, document=self.documents[i], score=float(scores[i]))
            for i in order
        ]

    def retrieve_from_text(self, query_text: str, top_n: int = 5) -> list[RetrievedPassage]:
        """Re-embeds `query_text` with THIS node's own local_embedder, then
        retrieves. This is the call a router/coordinator should make after
        selecting this node — it never needs to know which model the node
        uses internally.
        """
        if self.local_embedder is None:
            raise ValueError(
                f"node {self.source_id!r} has no local_embedder configured; "
                "pass one to InProcessNode(...) or use retrieve() with a "
                "precomputed vector in this node's own space"
            )
        query_embedding = np.asarray(self.local_embedder([query_text])[0], dtype=np.float64)
        return self.retrieve(query_embedding, top_n=top_n)


def build_simulated_source(
    source_id: str,
    documents: list[str],
    routing_embedder,
    local_embedder=None,
    *,
    k: int,
    sigma: float,
    rng: np.random.Generator,
    policy_labels: list | None = None,
    publish_metadata: bool = True,
    signing_key=None,
    psi: bool = True,
    deidentify: bool = True,
    known_identifiers: list[str] | None = None,
    deid_backend=None,
    deid_level: str = "basic",
    collections: list[str] | None = None,
    access_policy: dict[str, list[str]] | None = None,
) -> tuple[InProcessNode, SourceProfile]:
    """PII removal happens once per embedder call, on the same raw documents.

    `local_embedder` defaults to `routing_embedder` when omitted — i.e. no
    heterogeneity unless the caller explicitly opts a node into a different
    local model. The published profile is always built from `routing_embedder`
    output; the node's own index is always built from `local_embedder` output.
    The node also keeps the routing-space document embeddings as a second index
    for v2 vector dispatch (InProcessNode.retrieve_vector).

    `signing_key` (an Ed25519 private key, nodes/signing.py) signs the profile.
    For a simulated node the coordinator holds this key itself, so the
    signature exercises the verification path but proves nothing about a
    remote party — state that wherever simulated results are reported.
    """
    local_embedder = local_embedder or routing_embedder
    if deidentify:
        # Same node-side step as nodes/mcp_server (docs/44): the node never
        # holds, embeds, publishes or serves the raw text.
        from privacy.deidentify import Deidentifier

        _deid = Deidentifier(known_identifiers=known_identifiers or (), backend=deid_backend, level=deid_level)
        documents = _deid.redact_all(documents)
        deid_counts = {k: v for k, v in _deid.counts.items() if v}
    else:
        deid_counts = None

    routing_embeddings = embed_documents(documents, routing_embedder)
    local_embeddings = (
        routing_embeddings if local_embedder is routing_embedder else embed_documents(documents, local_embedder)
    )
    pub_docs, pub_emb = public_view(documents, routing_embeddings, collections)

    profile = build_profile(
        source_id,
        pub_emb,
        k=min(k, len(pub_docs)),
        sigma=sigma,
        rng=rng,
        document_count=len(pub_docs),   # restricted collection sizes are not published either
        policy_labels=policy_labels,
    )
    attach_metadata(profile, pub_docs, routing_embedder, enabled=publish_metadata)
    if signing_key is not None:
        from nodes.signing import sign_profile

        sign_profile(profile, signing_key)
    node = InProcessNode(
        source_id, documents, local_embeddings, local_embedder=local_embedder, routing_embeddings=routing_embeddings
    )
    node.deid_counts = deid_counts
    if psi:
        attach_psi_index(node, profile, seed=int(rng.integers(0, 2**31 - 1)),
                         collections=collections, access_policy=access_policy)
        if signing_key is not None:
            from nodes.signing import sign_profile

            sign_profile(profile, signing_key)  # re-sign: cluster centroids are covered
    return node, profile


def public_view(documents: list[str], routing_embeddings: np.ndarray, collections: list[str] | None):
    """What a node may publish (docs/45): its routing profile and metadata are
    built from `public` documents only when it also holds restricted
    collections, so neither the coarse centroids nor the topic words describe
    restricted content. A node with no public documents at all falls back to
    publishing from everything (it must be routable) — stated in docs/45."""
    if not collections or all(c == "public" for c in collections):
        return documents, routing_embeddings
    idx = [i for i, c in enumerate(collections) if c == "public"]
    if not idx:
        return documents, routing_embeddings
    return [documents[i] for i in idx], np.asarray(routing_embeddings)[idx]


def attach_psi_index(node: InProcessNode, profile: SourceProfile, *, seed: int, psi_key: bytes | None = None,
                     psi_keys: dict[str, bytes] | None = None, collections: list[str] | None = None,
                     access_policy: dict[str, list[str]] | None = None) -> None:
    """Build the node's cluster table and OPRF state, publish the centroids.
    Documents stay inside the node; only centroids (≥ min-size documents
    each) and encrypted envelopes ever leave.

    With `collections` (one label per document, docs/45) each collection is
    clustered separately and sealed under its own OPRF key, and the profile
    publishes which collection each cluster belongs to plus the node's
    role -> collections policy. Without it, everything is "public" and the
    result is byte-identical to the single-key node."""
    from privacy.cluster_index import build_cluster_index, build_cluster_index_by_collection
    from privacy.psi import PSINode

    if collections is not None:
        node.collections = list(collections)
    node.access_policy = dict(access_policy or {})
    if all(c == "public" for c in node.collections):
        centroids, clusters = build_cluster_index(node.documents, node.routing_embeddings, seed=seed)
        cluster_collections = None
        psi_node = PSINode(node.source_id, key=psi_key, keys=psi_keys)
        psi_node.build_table(clusters)
    else:
        centroids, clusters, cluster_collections = build_cluster_index_by_collection(
            node.documents, node.routing_embeddings, node.collections, seed=seed)
        psi_node = PSINode(node.source_id, keys=psi_keys or ({"public": psi_key} if psi_key else None))
        psi_node.build_table(clusters, {cid: c for cid, c in enumerate(cluster_collections)})
    node.psi = psi_node
    node.restricted_clusters = {}
    if cluster_collections is None:
        profile.cluster_centroids = centroids
        profile.cluster_collections = None
    else:
        # Role-scoped publication (docs/45): the profile carries only public
        # clusters (ids 0..n-1, see build_cluster_index_by_collection); the
        # node serves restricted centroids to permitted roles on request.
        n_public = sum(1 for c in cluster_collections if c == "public")
        profile.cluster_centroids = np.asarray(centroids)[:n_public]
        profile.cluster_collections = ["public"] * n_public
        node.restricted_clusters = {cid: (c, np.asarray(centroids)[cid]) for cid, c in enumerate(cluster_collections)
                                    if c != "public"}
    profile.access_policy = dict(access_policy) if access_policy else None


def forge_profile(profile: SourceProfile, target_centroids: np.ndarray) -> SourceProfile:
    """A3: a malicious source republishes centroids designed to attract
    queries it cannot actually serve well. The node's real retrieval behaviour
    (InProcessNode.retrieve) is unchanged — only the published profile lies.
    """
    forged = SourceProfile(**{**profile.__dict__})
    forged.centroids = np.asarray(target_centroids, dtype=np.float64)
    forged.profile_version = profile.profile_version + 1
    return forged
