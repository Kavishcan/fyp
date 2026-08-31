"""Synthetic source partitioning for scaling beyond the real MCP node counts
(docs/06-datasets.md node partitioning table).

Two strategies, deliberately kept separate because they produce different
routing difficulty and that difference must be stated plainly rather than
assumed away (docs/02-proposal.md RC5):

- "cluster": partitions by topic similarity, producing sources with coherent
  local corpora — this is what real institutions plausibly look like, but it
  is also the easier routing condition.
- "random": partitions independent of topic, producing sources with mixed,
  overlapping content — the same-domain hard-split control that stops
  cross-domain routing from looking artificially easy (docs/05-experiments.md
  "Known confound").
"""
from __future__ import annotations

import numpy as np

from nodes.profile import kmeans


def partition_random(n_documents: int, n_sources: int, rng: np.random.Generator) -> list[list[int]]:
    indices = rng.permutation(n_documents)
    return [list(chunk) for chunk in np.array_split(indices, n_sources)]


def partition_by_cluster(
    embeddings: np.ndarray, n_sources: int, rng: np.random.Generator
) -> list[list[int]]:
    embeddings = np.asarray(embeddings, dtype=np.float64)
    centroids = kmeans(embeddings, n_sources, rng)
    distances = np.linalg.norm(embeddings[:, None, :] - centroids[None, :, :], axis=-1)
    assignments = np.argmin(distances, axis=1)
    groups: list[list[int]] = [[] for _ in range(centroids.shape[0])]
    for doc_index, cluster in enumerate(assignments):
        groups[cluster].append(doc_index)
    return groups


def partition_corpus(
    embeddings: np.ndarray,
    n_sources: int,
    rng: np.random.Generator,
    strategy: str = "cluster",
) -> list[list[int]]:
    if strategy == "random":
        return partition_random(embeddings.shape[0], n_sources, rng)
    if strategy == "cluster":
        return partition_by_cluster(embeddings, n_sources, rng)
    raise ValueError(f"unknown strategy {strategy!r}, expected 'cluster' or 'random'")
