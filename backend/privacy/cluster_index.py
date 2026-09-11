"""Cluster-id index a node builds for PSI dispatch (docs/35, docs/03 target).

The node partitions its routing-space document embeddings with spherical
k-means at roughly `docs_per_cluster` documents per cluster, merges any
cluster below `min_size` into its nearest neighbour, and PUBLISHES the
resulting centroids next to its routing profile. The client assigns a query
to its nearest `nprobe` centroids locally; the cluster id is the PSI item.

docs/35 measured why: with ~10 docs per cluster, nprobe 2 and min size 5,
recall is 0.89 of dense@10 while ~36 passages are delivered per contact and
no published centroid stands for fewer than 5 documents (2% are within
cosine 0.95 of some document). Raising resolution without the minimum size
publishes document embeddings as centroids — never do that.

Passages in the cluster table carry their routing-space embedding so the
client can rerank decrypted passages exactly without a second embedding pass.
"""
from __future__ import annotations

import numpy as np

DEFAULT_DOCS_PER_CLUSTER = 10
DEFAULT_MIN_CLUSTER_SIZE = 5
DEFAULT_NPROBE = 2


def kmeans_unit(vectors: np.ndarray, k: int, seed: int, iters: int = 25) -> tuple[np.ndarray, np.ndarray]:
    """Spherical k-means. Returns unit centroids and per-vector assignments."""
    vectors = np.asarray(vectors, dtype=np.float64)
    rng = np.random.default_rng(seed)
    k = max(1, min(k, len(vectors)))
    centroids = vectors[rng.choice(len(vectors), k, replace=False)].copy()
    centroids /= np.maximum(np.linalg.norm(centroids, axis=1, keepdims=True), 1e-12)
    assign = np.argmax(vectors @ centroids.T, axis=1)
    for _ in range(iters):
        for j in range(k):
            members = vectors[assign == j]
            if len(members):
                centroids[j] = members.mean(axis=0)
        centroids /= np.maximum(np.linalg.norm(centroids, axis=1, keepdims=True), 1e-12)
        new_assign = np.argmax(vectors @ centroids.T, axis=1)
        if (new_assign == assign).all():
            break
        assign = new_assign
    return centroids, assign


def enforce_min_cluster_size(
    vectors: np.ndarray, centroids: np.ndarray, assign: np.ndarray, min_size: int
) -> tuple[np.ndarray, np.ndarray]:
    """Merge every cluster smaller than `min_size` into its nearest other
    cluster until none remain, recomputing centroids. A published centroid
    then never stands for fewer than `min_size` documents."""
    if min_size <= 1:
        return centroids, assign
    vectors = np.asarray(vectors, dtype=np.float64)
    centroids = np.asarray(centroids, dtype=np.float64).copy()
    assign = np.asarray(assign).copy()
    while True:
        ids, sizes = np.unique(assign, return_counts=True)
        small = ids[sizes < min_size]
        if len(small) == 0 or len(ids) == 1:
            break
        j = small[np.argmin(sizes[sizes < min_size])]
        others = ids[ids != j]
        target = others[np.argmax(centroids[others] @ centroids[j])]
        assign[assign == j] = target
        members = vectors[assign == target]
        centroids[target] = members.mean(axis=0)
        centroids[target] /= max(float(np.linalg.norm(centroids[target])), 1e-12)
    live = np.unique(assign)
    remap = {int(old): new for new, old in enumerate(live.tolist())}
    return centroids[live], np.array([remap[int(a)] for a in assign])


def build_cluster_index(
    documents: list[str],
    routing_embeddings: np.ndarray,
    *,
    seed: int,
    docs_per_cluster: int = DEFAULT_DOCS_PER_CLUSTER,
    min_size: int = DEFAULT_MIN_CLUSTER_SIZE,
) -> tuple[np.ndarray, dict[int, list[dict]]]:
    """Returns (centroids to publish, cluster id -> passages). Each passage is
    {"document": text, "embedding": routing-space vector as a list}."""
    if len(documents) != len(routing_embeddings):
        raise ValueError("documents and routing_embeddings must be the same length")
    if not documents:
        return np.empty((0, 0)), {}
    vectors = np.asarray(routing_embeddings, dtype=np.float64)
    unit = vectors / np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-12)
    k = max(1, round(len(documents) / docs_per_cluster))
    centroids, assign = kmeans_unit(unit, k, seed)
    centroids, assign = enforce_min_cluster_size(unit, centroids, assign, min(min_size, len(documents)))
    clusters: dict[int, list[dict]] = {}
    for idx, cid in enumerate(assign.tolist()):
        clusters.setdefault(int(cid), []).append({"document": documents[idx], "embedding": vectors[idx].tolist()})
    return centroids, clusters


def assign_clusters(query_vector: np.ndarray, centroids: np.ndarray, nprobe: int = DEFAULT_NPROBE) -> list[int]:
    """Client side: the `nprobe` nearest published centroids, by cosine."""
    if centroids is None or len(centroids) == 0:
        return []
    q = np.asarray(query_vector, dtype=np.float64)
    q = q / (np.linalg.norm(q) or 1.0)
    scores = np.asarray(centroids, dtype=np.float64) @ q
    order = np.argsort(-scores)[: max(1, min(nprobe, len(scores)))]
    return [int(i) for i in order]


def rerank_passages(query_vector: np.ndarray, passages: list[dict], top_n: int) -> list[tuple[str, float]]:
    """Exact cosine over decrypted passages, on the device."""
    if not passages:
        return []
    q = np.asarray(query_vector, dtype=np.float64)
    q = q / (np.linalg.norm(q) or 1.0)
    embeddings = np.asarray([p["embedding"] for p in passages], dtype=np.float64)
    norms = np.maximum(np.linalg.norm(embeddings, axis=1), 1e-12)
    scores = (embeddings @ q) / norms
    order = np.argsort(-scores)[:top_n]
    return [(passages[i]["document"], float(scores[i])) for i in order]
