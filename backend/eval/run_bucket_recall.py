"""E1/E2 (docs/35): bucket recall of semantic hashing for PSI-based private retrieval.

Under labeled PSI a node can only answer "is this exact hash id in my table?"
— it cannot compute cosine similarity. Retrieval therefore becomes: hash the
query embedding to a short code (SimHash: signs of random projections), probe
that code and its Hamming neighbours, and receive every document whose code
collides. This measures, with NO cryptography, whether a question and its
relevant passage land in the same bucket often enough for that to work.

Two numbers per configuration, which pull in opposite directions:
- bucket_recall    fraction of queries for which at least one qrel-relevant
                   document is in a probed bucket (any table). Compared with
                   dense_recall@10 from exact cosine over the same pool.
- envelopes        mean distinct documents in the probed buckets — what the
                   node would deliver, i.e. node-side disclosure per query.

Each BEIR corpus is one node pool (a few thousand documents). Multi-node
routing is orthogonal: PSI is pairwise per node, so collisions only happen
within a node's own table. Hash randomness is seeded; three seeds are
reported. Query and document embeddings are the same bge-base vectors used in
docs/31–33, via the on-disk cache.

Two bucketing schemes:
- `simhash`   signs of random projections (LSH for cosine), multi-probe by
              Hamming radius, several tables. Data-independent.
- `cluster`   k-means centroids of the node's own documents are PUBLISHED
              (exactly as routing profiles already are); the client assigns
              the query to its nearest `nprobe` centroids locally and the
              bucket id is the cluster id. IVF-style. Data-dependent, so the
              centroids disclose the node's topic structure at resolution k.

Not measured: PSI cost, adversarial collisions, learned hash functions.

Run: python -m eval.run_bucket_recall
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import time
from itertools import combinations
from math import comb

import numpy as np

from eval.embed_cache import CachedEmbedder
from eval.sweep import (
    BEIR_DIR,
    RESULTS_DIR,
    HashingEmbedder,
    SentenceTransformerEmbedder,
    collect_documents,
    load_qrels,
    select_queries,
)


# --- SimHash ----------------------------------------------------------------


def simhash_planes(dim: int, bits: int, tables: int, seed: int) -> np.ndarray:
    """(tables, dim, bits) Gaussian hyperplanes; public parameters shared by
    client and every node."""
    return np.random.default_rng(seed).standard_normal((tables, dim, bits))


def simhash_codes(vectors: np.ndarray, planes: np.ndarray) -> np.ndarray:
    """(n, tables) integer codes. Bit b of table t is sign(v · planes[t,:,b])."""
    bits = planes.shape[2]
    weights = (1 << np.arange(bits, dtype=np.uint64))
    codes = np.empty((vectors.shape[0], planes.shape[0]), dtype=np.uint64)
    for t in range(planes.shape[0]):
        signs = (vectors @ planes[t]) > 0
        codes[:, t] = signs.astype(np.uint64) @ weights
    return codes


def hamming_neighbours(code: int, bits: int, radius: int) -> list[int]:
    """All codes within Hamming distance <= radius (the multi-probe set)."""
    out = [code]
    for r in range(1, radius + 1):
        for flips in combinations(range(bits), r):
            mask = 0
            for b in flips:
                mask |= 1 << b
            out.append(code ^ mask)
    return out


def probes_per_query(bits: int, radius: int, tables: int) -> int:
    return tables * sum(comb(bits, r) for r in range(radius + 1))


# --- cluster ids --------------------------------------------------------------


def kmeans_unit(vectors: np.ndarray, k: int, seed: int, iters: int = 25) -> tuple[np.ndarray, np.ndarray]:
    """Spherical k-means. Returns unit centroids and per-vector assignments."""
    rng = np.random.default_rng(seed)
    k = min(k, len(vectors))
    centroids = vectors[rng.choice(len(vectors), k, replace=False)].copy()
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
    then never stands for fewer than `min_size` documents — k-anonymity on
    the centroid, so it cannot be a single document's embedding in disguise.
    """
    if min_size <= 1:
        return centroids, assign
    assign = assign.copy()
    while True:
        ids, sizes = np.unique(assign, return_counts=True)
        small = ids[sizes < min_size]
        if len(small) == 0 or len(ids) == 1:
            break
        j = small[np.argmin(sizes[sizes < min_size])]  # smallest first
        others = ids[ids != j]
        target = others[np.argmax(centroids[others] @ centroids[j])]
        assign[assign == j] = target
        members = vectors[assign == target]
        centroids[target] = members.mean(axis=0)
        centroids[target] /= max(float(np.linalg.norm(centroids[target])), 1e-12)
    # Compact ids so downstream can index centroids densely.
    live = np.unique(assign)
    remap = {old: new for new, old in enumerate(live.tolist())}
    return centroids[live], np.vectorize(remap.get)(assign)


def centroid_leak(doc_vectors: np.ndarray, centroids: np.ndarray, assign: np.ndarray, threshold: float = 0.95) -> dict:
    """How far published centroids go toward publishing document embeddings."""
    sizes = np.bincount(assign, minlength=len(centroids))
    nearest = np.max(doc_vectors @ centroids.T, axis=0)
    return {
        "clusters_published": int(len(centroids)),
        "singleton_fraction": float(np.mean(sizes == 1)),
        "min_cluster_size_observed": int(sizes.min()),
        "centroid_near_doc_fraction": float(np.mean(nearest > threshold)),
    }


def cluster_recall(
    query_vectors: np.ndarray,
    doc_vectors: np.ndarray,
    relevant: list[set[int]],
    *,
    k: int,
    nprobe: int,
    seed: int,
    min_size: int = 1,
) -> dict:
    centroids, assign = kmeans_unit(doc_vectors, k, seed)
    centroids, assign = enforce_min_cluster_size(doc_vectors, centroids, assign, min_size)
    members = {j: set(np.where(assign == j)[0].tolist()) for j in range(len(centroids))}
    nearest = np.argsort(-(query_vectors @ centroids.T), axis=1)[:, :nprobe]
    hits, envelopes = [], []
    for q_idx in range(query_vectors.shape[0]):
        delivered: set[int] = set()
        for j in nearest[q_idx].tolist():
            delivered |= members[j]
        hits.append(1.0 if delivered & relevant[q_idx] else 0.0)
        envelopes.append(len(delivered))
    return {
        "bucket_recall": float(np.mean(hits)),
        "envelopes": float(np.mean(envelopes)),
        "envelopes_p95": float(np.percentile(envelopes, 95)),
        "probes": min(nprobe, len(centroids)),
        **centroid_leak(doc_vectors, centroids, assign),
    }


# --- measurement ------------------------------------------------------------


def bucket_recall(
    query_vectors: np.ndarray,
    doc_vectors: np.ndarray,
    relevant: list[set[int]],
    *,
    bits: int,
    radius: int,
    tables: int,
    seed: int,
) -> dict:
    planes = simhash_planes(doc_vectors.shape[1], bits, tables, seed)
    doc_codes = simhash_codes(doc_vectors, planes)
    query_codes = simhash_codes(query_vectors, planes)

    buckets: list[dict[int, list[int]]] = []
    for t in range(tables):
        table: dict[int, list[int]] = {}
        for doc_idx, code in enumerate(doc_codes[:, t].tolist()):
            table.setdefault(code, []).append(doc_idx)
        buckets.append(table)

    hits, envelopes = [], []
    for q_idx in range(query_vectors.shape[0]):
        delivered: set[int] = set()
        for t in range(tables):
            for code in hamming_neighbours(int(query_codes[q_idx, t]), bits, radius):
                delivered.update(buckets[t].get(code, ()))
        hits.append(1.0 if delivered & relevant[q_idx] else 0.0)
        envelopes.append(len(delivered))
    return {
        "bucket_recall": float(np.mean(hits)),
        "envelopes": float(np.mean(envelopes)),
        "envelopes_p95": float(np.percentile(envelopes, 95)),
        "probes": probes_per_query(bits, radius, tables),
    }


def dense_recall(query_vectors: np.ndarray, doc_vectors: np.ndarray, relevant: list[set[int]], k: int) -> float:
    scores = query_vectors @ doc_vectors.T
    top = np.argpartition(-scores, min(k, scores.shape[1] - 1), axis=1)[:, :k]
    return float(np.mean([1.0 if set(top[i].tolist()) & relevant[i] else 0.0 for i in range(len(relevant))]))


def load_pool(corpus: str, n_queries: int, pool_size: int, seed: int):
    """One node pool: doc ids/texts, query ids/texts, relevant doc indices."""
    corpus_dir = BEIR_DIR / corpus
    rng = random.Random(seed)
    qrels = load_qrels(corpus_dir)
    queries = select_queries(corpus_dir, qrels, n_queries, rng)
    required = {did for qid in queries for did in qrels[qid]}
    documents = collect_documents(corpus_dir, required, pool_size, rng, allow_missing=True)
    doc_ids = list(documents)
    index = {did: i for i, did in enumerate(doc_ids)}
    kept_q, relevant = [], []
    for qid, text in queries.items():
        rel = {index[d] for d in qrels[qid] if d in index}
        if rel:
            kept_q.append((qid, text))
            relevant.append(rel)
    return doc_ids, [documents[d] for d in doc_ids], kept_q, relevant


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpora", nargs="+", default=["arguana", "nfcorpus", "scifact", "fiqa", "scidocs"])
    parser.add_argument("--n-queries-per-corpus", type=int, default=100)
    parser.add_argument("--pool-size", type=int, default=2000, help="documents per node pool (plus qrel-required)")
    parser.add_argument("--scheme", choices=["simhash", "cluster"], default="simhash")
    parser.add_argument("--clusters", nargs="+", type=int, default=[50, 100, 200], help="cluster scheme: k")
    parser.add_argument("--nprobe", nargs="+", type=int, default=[1, 2, 4, 8], help="cluster scheme: centroids probed")
    parser.add_argument("--min-cluster-size", nargs="+", type=int, default=[1],
                        help="cluster scheme: merge clusters smaller than this (1 = no rule)")
    parser.add_argument("--bits", nargs="+", type=int, default=[16, 32, 64])
    parser.add_argument("--radius", nargs="+", type=int, default=[0, 1, 2])
    parser.add_argument("--tables", nargs="+", type=int, default=[1, 4, 8])
    parser.add_argument("--dense-k", type=int, default=10)
    parser.add_argument("--data-seed", type=int, default=11)
    parser.add_argument("--hash-seeds", nargs="+", type=int, default=[1, 2, 3])
    parser.add_argument("--embedder", choices=["sentence-transformer", "hashing"], default="sentence-transformer")
    parser.add_argument("--embedder-model", default="BAAI/bge-base-en-v1.5")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = time.strftime("%Y%m%d-%H%M%S")
    embedder = (
        CachedEmbedder(SentenceTransformerEmbedder(args.embedder_model))
        if args.embedder == "sentence-transformer" else HashingEmbedder()
    )

    rows: list[dict] = []
    for corpus in args.corpora:
        started = time.perf_counter()
        doc_ids, doc_texts, queries, relevant = load_pool(corpus, args.n_queries_per_corpus, args.pool_size, args.data_seed)
        docs = embedder.embed(doc_texts)
        docs = docs / np.maximum(np.linalg.norm(docs, axis=1, keepdims=True), 1e-12)
        qv = embedder.embed([t for _, t in queries])
        qv = qv / np.maximum(np.linalg.norm(qv, axis=1, keepdims=True), 1e-12)
        dense10 = dense_recall(qv, docs, relevant, args.dense_k)
        print(f"{corpus}: {len(doc_ids)} docs, {len(queries)} queries, dense@{args.dense_k} {dense10:.3f}, "
              f"prepared in {time.perf_counter() - started:.0f}s", flush=True)
        if args.scheme == "simhash":
            grid = [{"bits": b, "radius": r, "tables": t} for b in args.bits for r in args.radius for t in args.tables]
        else:
            grid = [{"clusters": k, "nprobe": n, "min_size": m}
                    for k in args.clusters for n in args.nprobe for m in args.min_cluster_size]
        for params in grid:
            for hseed in args.hash_seeds:
                if args.scheme == "simhash":
                    r = bucket_recall(qv, docs, relevant, bits=params["bits"], radius=params["radius"],
                                      tables=params["tables"], seed=hseed)
                else:
                    r = cluster_recall(qv, docs, relevant, k=params["clusters"], nprobe=params["nprobe"],
                                       seed=hseed, min_size=params["min_size"])
                r.update({"scheme": args.scheme, **params, "corpus": corpus, "docs": len(doc_ids),
                          "queries": len(queries), "hash_seed": hseed,
                          f"dense_recall@{args.dense_k}": dense10,
                          "dense_recall@envelopes": dense_recall(qv, docs, relevant, max(1, int(round(r["envelopes"])))),
                          "ratio": r["bucket_recall"] / dense10 if dense10 else float("nan"),
                          "relevant_per_query": float(np.mean([len(x) for x in relevant])),
                          "envelopes_per_relevant": r["envelopes"] / float(np.mean([len(x) for x in relevant]))})
                rows.append(r)
            last = rows[-len(args.hash_seeds):]
            print(f"  {params}: bucket {np.mean([x['bucket_recall'] for x in last]):.3f} "
                  f"envelopes {np.mean([x['envelopes'] for x in last]):.1f} probes {last[0]['probes']}", flush=True)
        _write(RESULTS_DIR / f"bucket_recall_{args.scheme}_{run_id}_per_corpus.csv", rows)

    keys = ("bits", "radius", "tables") if args.scheme == "simhash" else ("clusters", "nprobe", "min_size")
    summary = []
    for key in dict.fromkeys(tuple(r[k] for k in keys) for r in rows):
        group = [r for r in rows if tuple(r[k] for k in keys) == key]
        entry = {"scheme": args.scheme, **dict(zip(keys, key)), "probes": group[0]["probes"]}
        metrics = ["bucket_recall", f"dense_recall@{args.dense_k}", "dense_recall@envelopes", "ratio",
                   "envelopes", "envelopes_p95", "envelopes_per_relevant"]
        if args.scheme == "cluster":
            metrics += ["clusters_published", "singleton_fraction", "min_cluster_size_observed", "centroid_near_doc_fraction"]
        for metric in metrics:
            entry[metric] = float(np.mean([r[metric] for r in group]))
        entry.update({"corpora": len({r["corpus"] for r in group}), "hash_seeds": len({r["hash_seed"] for r in group})})
        summary.append(entry)
    _write(RESULTS_DIR / f"bucket_recall_{args.scheme}_{run_id}.csv", summary)
    print(json.dumps(summary, indent=2))


def _write(path, rows: list[dict]) -> None:
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
