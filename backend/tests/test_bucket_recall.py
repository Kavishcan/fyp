"""Tests for the semantic-hash bucket-recall harness (E1/E2). They check the
harness measures what it claims; they say nothing about whether hashing
retrieves well — that is what the experiment reports."""
from __future__ import annotations

import numpy as np

from eval.run_bucket_recall import (
    bucket_recall,
    centroid_leak,
    cluster_recall,
    enforce_min_cluster_size,
    kmeans_unit,
    dense_recall,
    hamming_neighbours,
    probes_per_query,
    simhash_codes,
    simhash_planes,
)


def test_identical_vectors_share_a_code_in_every_table():
    planes = simhash_planes(8, 16, tables=4, seed=0)
    v = np.random.default_rng(1).standard_normal((1, 8))
    codes = simhash_codes(np.vstack([v, v]), planes)
    assert (codes[0] == codes[1]).all()


def test_opposite_vectors_share_no_bits():
    planes = simhash_planes(8, 16, tables=1, seed=0)
    v = np.random.default_rng(1).standard_normal((1, 8))
    codes = simhash_codes(np.vstack([v, -v]), planes)
    assert int(codes[0, 0]) ^ int(codes[1, 0]) == (1 << 16) - 1


def test_hamming_neighbours_count_matches_formula():
    assert len(hamming_neighbours(0b1010, bits=8, radius=0)) == 1
    assert len(hamming_neighbours(0b1010, bits=8, radius=1)) == 1 + 8
    assert len(hamming_neighbours(0b1010, bits=8, radius=2)) == 1 + 8 + 28
    assert probes_per_query(8, 2, tables=3) == 3 * 37
    assert 0b1010 ^ 0b0001 in hamming_neighbours(0b1010, bits=8, radius=1)


def test_query_equal_to_its_relevant_doc_is_always_recalled():
    rng = np.random.default_rng(3)
    docs = rng.standard_normal((50, 16))
    docs /= np.linalg.norm(docs, axis=1, keepdims=True)
    queries = docs[:10].copy()
    relevant = [{i} for i in range(10)]
    r = bucket_recall(queries, docs, relevant, bits=32, radius=0, tables=1, seed=0)
    assert r["bucket_recall"] == 1.0
    assert r["envelopes"] >= 1.0
    assert r["probes"] == 1


def test_wider_probing_never_lowers_recall_and_never_lowers_envelopes():
    rng = np.random.default_rng(4)
    docs = rng.standard_normal((300, 16))
    docs /= np.linalg.norm(docs, axis=1, keepdims=True)
    queries = docs[:40] + 0.4 * rng.standard_normal((40, 16))
    queries /= np.linalg.norm(queries, axis=1, keepdims=True)
    relevant = [{i} for i in range(40)]
    narrow = bucket_recall(queries, docs, relevant, bits=16, radius=0, tables=1, seed=0)
    wide = bucket_recall(queries, docs, relevant, bits=16, radius=2, tables=4, seed=0)
    assert wide["bucket_recall"] >= narrow["bucket_recall"]
    assert wide["envelopes"] >= narrow["envelopes"]


def test_dense_recall_finds_exact_match_at_k1():
    rng = np.random.default_rng(5)
    docs = rng.standard_normal((20, 8))
    docs /= np.linalg.norm(docs, axis=1, keepdims=True)
    assert dense_recall(docs[:5], docs, [{i} for i in range(5)], k=1) == 1.0


def test_kmeans_returns_unit_centroids_and_full_assignment():
    rng = np.random.default_rng(6)
    docs = rng.standard_normal((60, 8))
    docs /= np.linalg.norm(docs, axis=1, keepdims=True)
    centroids, assign = kmeans_unit(docs, k=5, seed=0)
    assert centroids.shape == (5, 8)
    assert np.allclose(np.linalg.norm(centroids, axis=1), 1.0)
    assert assign.shape == (60,) and set(assign.tolist()) <= set(range(5))


def test_cluster_scheme_recalls_a_query_equal_to_its_document():
    rng = np.random.default_rng(7)
    docs = rng.standard_normal((80, 8))
    docs /= np.linalg.norm(docs, axis=1, keepdims=True)
    r = cluster_recall(docs[:10], docs, [{i} for i in range(10)], k=8, nprobe=1, seed=0)
    assert r["bucket_recall"] == 1.0
    assert r["probes"] == 1
    # Delivered set is the whole cluster, never fewer than one document.
    assert r["envelopes"] >= 1.0


def test_more_probes_never_lower_cluster_recall_or_envelopes():
    rng = np.random.default_rng(8)
    docs = rng.standard_normal((200, 8))
    docs /= np.linalg.norm(docs, axis=1, keepdims=True)
    queries = docs[:30] + 0.5 * rng.standard_normal((30, 8))
    queries /= np.linalg.norm(queries, axis=1, keepdims=True)
    rel = [{i} for i in range(30)]
    one = cluster_recall(queries, docs, rel, k=20, nprobe=1, seed=0)
    four = cluster_recall(queries, docs, rel, k=20, nprobe=4, seed=0)
    assert four["bucket_recall"] >= one["bucket_recall"]
    assert four["envelopes"] >= one["envelopes"]


def test_min_cluster_size_leaves_no_cluster_below_the_minimum():
    rng = np.random.default_rng(9)
    docs = rng.standard_normal((120, 8))
    docs /= np.linalg.norm(docs, axis=1, keepdims=True)
    centroids, assign = kmeans_unit(docs, k=60, seed=0)          # ~2 docs per cluster
    merged_c, merged_a = enforce_min_cluster_size(docs, centroids, assign, min_size=5)
    sizes = np.bincount(merged_a, minlength=len(merged_c))
    assert sizes.min() >= 5
    assert len(merged_c) < 60
    assert set(merged_a.tolist()) == set(range(len(merged_c)))  # dense ids
    assert np.allclose(np.linalg.norm(merged_c, axis=1), 1.0)


def test_min_cluster_size_one_is_a_no_op():
    rng = np.random.default_rng(10)
    docs = rng.standard_normal((40, 8))
    centroids, assign = kmeans_unit(docs, k=8, seed=0)
    c2, a2 = enforce_min_cluster_size(docs, centroids, assign, min_size=1)
    assert (a2 == assign).all() and np.allclose(c2, centroids)


def test_centroid_leak_is_total_when_every_doc_is_its_own_cluster():
    rng = np.random.default_rng(11)
    docs = rng.standard_normal((30, 8))
    docs /= np.linalg.norm(docs, axis=1, keepdims=True)
    leak = centroid_leak(docs, docs.copy(), np.arange(30))
    assert leak["singleton_fraction"] == 1.0
    assert leak["centroid_near_doc_fraction"] == 1.0
    assert leak["min_cluster_size_observed"] == 1


def test_min_cluster_size_removes_singleton_centroids_in_recall_output():
    rng = np.random.default_rng(12)
    docs = rng.standard_normal((200, 8))
    docs /= np.linalg.norm(docs, axis=1, keepdims=True)
    rel = [{i} for i in range(20)]
    raw = cluster_recall(docs[:20], docs, rel, k=150, nprobe=2, seed=0)
    safe = cluster_recall(docs[:20], docs, rel, k=150, nprobe=2, seed=0, min_size=5)
    assert raw["singleton_fraction"] > 0.0
    assert safe["singleton_fraction"] == 0.0
    assert safe["min_cluster_size_observed"] >= 5
