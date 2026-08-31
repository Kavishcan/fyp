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
    ) -> None:
        if len(documents) != len(document_embeddings):
            raise ValueError("documents and document_embeddings must be the same length")
        self.source_id = source_id
        self.documents = documents
        self.document_embeddings = np.asarray(document_embeddings, dtype=np.float64)
        # Kept so retrieve_from_text can re-embed a raw query in this node's
        # own space; optional so existing vector-based callers/tests still work.
        self.local_embedder = local_embedder

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
) -> tuple[InProcessNode, SourceProfile]:
    """PII removal happens once per embedder call, on the same raw documents.

    `local_embedder` defaults to `routing_embedder` when omitted — i.e. no
    heterogeneity unless the caller explicitly opts a node into a different
    local model. The published profile is always built from `routing_embedder`
    output; the node's own index is always built from `local_embedder` output.
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
    node = InProcessNode(source_id, documents, local_embeddings, local_embedder=local_embedder)
    return node, profile


def forge_profile(profile: SourceProfile, target_centroids: np.ndarray) -> SourceProfile:
    """A3: a malicious source republishes centroids designed to attract
    queries it cannot actually serve well. The node's real retrieval behaviour
    (InProcessNode.retrieve) is unchanged — only the published profile lies.
    """
    forged = SourceProfile(**{**profile.__dict__})
    forged.centroids = np.asarray(target_centroids, dtype=np.float64)
    forged.profile_version = profile.profile_version + 1
    return forged
