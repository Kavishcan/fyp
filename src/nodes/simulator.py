"""In-process source simulation for scaling beyond real MCP transport.

docs/03-architecture.md: real MCP servers demonstrate the architecture over an
actual protocol at 8-16 sources; this module provides the same retrieval
behaviour without network transport for the 100/300/1000-source scaling study.
The split must be stated explicitly wherever results are reported — this
module is the simulated half, not a substitute claimed to be "live."
"""
from __future__ import annotations

from dataclasses import dataclass

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

    def __init__(self, source_id: str, documents: list[str], document_embeddings: np.ndarray) -> None:
        if len(documents) != len(document_embeddings):
            raise ValueError("documents and document_embeddings must be the same length")
        self.source_id = source_id
        self.documents = documents
        self.document_embeddings = np.asarray(document_embeddings, dtype=np.float64)

    def retrieve(self, query_embedding: np.ndarray, top_n: int = 5) -> list[RetrievedPassage]:
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


def build_simulated_source(
    source_id: str,
    documents: list[str],
    embedder,
    *,
    k: int,
    sigma: float,
    rng: np.random.Generator,
    policy_labels: list | None = None,
) -> tuple[InProcessNode, SourceProfile]:
    """PII removal and embedding happen once here; the node keeps the
    embeddings for retrieval, and a separately-perturbed copy of their
    k-means centroids is published as the SourceProfile.
    """
    embeddings = embed_documents(documents, embedder)
    profile = build_profile(
        source_id,
        embeddings,
        k=k,
        sigma=sigma,
        rng=rng,
        document_count=len(documents),
        policy_labels=policy_labels,
    )
    node = InProcessNode(source_id, documents, embeddings)
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
