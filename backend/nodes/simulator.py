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
        # v2 (docs/30): a second index in the SHARED routing space so the
        # coordinator can dispatch a vector instead of raw query text. Costs the
        # node retrieval-model heterogeneity for that mode — the shared encoder,
        # not the node's own local model, does v2 retrieval.
        if routing_embeddings is not None and len(routing_embeddings) != len(documents):
            raise ValueError("documents and routing_embeddings must be the same length")
        self.routing_embeddings = None if routing_embeddings is None else np.asarray(routing_embeddings, dtype=np.float64)

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
        scores = (self.routing_embeddings @ q) / (doc_norms * q_norm)
        order = np.argsort(scores)[::-1][:top_n]
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
        scores = (self.document_embeddings @ q) / (doc_norms * q_norm)
        order = np.argsort(scores)[::-1][:top_n]
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

    routing_embeddings = embed_documents(documents, routing_embedder)
    local_embeddings = (
        routing_embeddings if local_embedder is routing_embedder else embed_documents(documents, local_embedder)
    )

    profile = build_profile(
        source_id,
        routing_embeddings,
        k=k,
        sigma=sigma,
        rng=rng,
        document_count=len(documents),
        policy_labels=policy_labels,
    )
    attach_metadata(profile, documents, routing_embedder, enabled=publish_metadata)
    if signing_key is not None:
        from nodes.signing import sign_profile

        sign_profile(profile, signing_key)
    node = InProcessNode(
        source_id, documents, local_embeddings, local_embedder=local_embedder, routing_embeddings=routing_embeddings
    )
    if psi:
        attach_psi_index(node, profile, seed=int(rng.integers(0, 2**31 - 1)))
        if signing_key is not None:
            from nodes.signing import sign_profile

            sign_profile(profile, signing_key)  # re-sign: cluster centroids are covered
    return node, profile


def attach_psi_index(node: InProcessNode, profile: SourceProfile, *, seed: int, psi_key: bytes | None = None) -> None:
    """Build the node's cluster table and OPRF state, publish the centroids.
    Documents stay inside the node; only centroids (≥ min-size documents
    each) and encrypted envelopes ever leave."""
    from privacy.cluster_index import build_cluster_index
    from privacy.psi import PSINode

    centroids, clusters = build_cluster_index(node.documents, node.routing_embeddings, seed=seed)
    psi_node = PSINode(node.source_id, key=psi_key)
    psi_node.build_table(clusters)
    node.psi = psi_node
    profile.cluster_centroids = centroids


def forge_profile(profile: SourceProfile, target_centroids: np.ndarray) -> SourceProfile:
    """A3: a malicious source republishes centroids designed to attract
    queries it cannot actually serve well. The node's real retrieval behaviour
    (InProcessNode.retrieve) is unchanged — only the published profile lies.
    """
    forged = SourceProfile(**{**profile.__dict__})
    forged.centroids = np.asarray(target_centroids, dtype=np.float64)
    forged.profile_version = profile.profile_version + 1
    return forged
