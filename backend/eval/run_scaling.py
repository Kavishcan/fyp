"""Source-count scaling study for the routing modes (docs/33).

docs/31 compared legacy, smart and v2 at 12–24 sources. The proposal's own
evaluation plan promises 30 / 100 / 300 / 1,000 clients, routing latency and
communication volume, none of which had been measured. This runs the same
matched-budget comparison at each source count and adds the two missing cost
metrics.

These are VIRTUAL source partitions of real BEIR corpora routed in-process:
one Python process, no MCP transport, no network. A 1,000-source row here is
a 1,000-profile routing result, not a 1,000-server deployment (CLAUDE.md).
Transport cost with real subprocess-backed nodes is measured separately by
eval/run_mcp_transport.py.

Per (source count, mode):
- source_recall / contacts / audit_cost / a2_precision as in docs/31.
- routing_latency_ms   wall time of the selection call only (embedding the
                       query is excluded; retrieval is not performed). Every
                       mode rebuilds its candidate index per query, exactly as
                       the live api/state.py path does, so this is the cost of
                       the shipped implementation, not of an optimised one.
- request_bytes        UTF-8 length of the JSON request each contacted node
                       would receive, summed over contacts. v2 sends a
                       routing-space vector; every other mode sends the query
                       text. Application payload only — no MCP framing, no
                       transport overhead, no responses.

Corpora are limited to those with enough judged queries and small enough
corpus files to repartition per seed (trec-covid has 50 queries with ~1,300
qrels each and is excluded). Small corpora cannot supply `docs_per_node` at
the largest tiers, so mean documents per source is reported and shrinks.

Run: python -m eval.run_scaling
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import time

import numpy as np

from attacks.a2_source_inference import SourceInferenceObserver
from eval.embed_cache import CachedEmbedder
from eval.run_mode_comparison import _topic_key, dispatch_for_mode
from eval.sweep import (
    RESULTS_DIR,
    HashingEmbedder,
    SentenceTransformerEmbedder,
    _normalise,
    build_dataset,
    build_node_profiles,
)
from router.v2 import dispatch_payload

MODES = ("broadcast", "oracle", "smart", "v2", "legacy")


def request_bytes_for(mode: str, query_text: str, query_vec: np.ndarray, top_n: int = 1) -> int:
    """Bytes of the request one contacted node receives in this mode."""
    if mode == "v2":
        body = dispatch_payload(query_vec, top_n=top_n)
    else:
        body = {"query": query_text, "top_n": top_n}
    return len(json.dumps(body).encode("utf-8"))


def run_mode_at_scale(
    mode: str,
    profiles: dict,
    queries: dict[str, str],
    query_vectors: dict[str, np.ndarray],
    relevant_nodes: dict[str, set[str]],
    *,
    max_nodes: int,
    genuine_k: int,
    coarse_k: int,
    seed: int,
) -> dict:
    rng = np.random.default_rng(seed)
    query_ids = list(query_vectors)
    random.Random(seed).shuffle(query_ids)

    observer = SourceInferenceObserver()
    topic_truth: dict[str, set[str]] = {}
    topic_counts: dict[str, int] = {}

    hits, contacts, audit, latencies, req_bytes = [], [], [], [], []
    for qid in query_ids:
        relevant = relevant_nodes[qid]
        topic_key = _topic_key(relevant)
        started = time.perf_counter()
        dispatched = dispatch_for_mode(
            mode, query_vectors[qid], profiles, topic_key, relevant,
            max_nodes=max_nodes, genuine_k=genuine_k, coarse_k=coarse_k, sigma=0.0, rng=rng,
        )
        latencies.append((time.perf_counter() - started) * 1000.0)
        hits.append(1.0 if set(dispatched) & relevant else 0.0)
        contacts.append(len(dispatched))
        audit.append(len([s for s in dispatched if s not in relevant]))
        req_bytes.append(request_bytes_for(mode, queries[qid], query_vectors[qid]) * len(dispatched))
        observer.observe(topic_key, dispatched)
        topic_truth[topic_key] = relevant
        topic_counts[topic_key] = topic_counts.get(topic_key, 0) + 1

    precisions = []
    for topic_key, truth in topic_truth.items():
        if topic_counts[topic_key] < 2 or not truth:
            continue
        guess = set(observer.infer_topic_sources(topic_key, len(truth)))
        if guess:
            precisions.append(len(guess & truth) / len(guess))

    return {
        "mode": mode,
        "sources": len(profiles),
        "queries": len(query_ids),
        "source_recall": float(np.mean(hits)),
        "contacts": float(np.mean(contacts)),
        "audit_cost": float(np.mean(audit)),
        "a2_precision": float(np.mean(precisions)) if precisions else float("nan"),
        "a2_topics": len(precisions),
        "routing_latency_ms": float(np.mean(latencies)),
        "routing_latency_p95_ms": float(np.percentile(latencies, 95)),
        "request_bytes": float(np.mean(req_bytes)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpora", nargs="+", default=["arguana", "nfcorpus", "scifact", "fiqa", "scidocs"])
    parser.add_argument("--nodes-per-corpus", nargs="+", type=int, default=[6, 20, 60, 200],
                        help="one tier per value; total sources = value x len(corpora)")
    parser.add_argument("--docs-per-node", type=int, default=40)
    parser.add_argument("--n-queries-per-corpus", type=int, default=100)
    parser.add_argument("--max-nodes", type=int, default=6)
    parser.add_argument("--genuine-k", type=int, default=2)
    parser.add_argument("--coarse-k", type=int, default=12)
    parser.add_argument("--seeds", nargs="+", type=int, default=[11, 22, 33])
    parser.add_argument("--modes", nargs="+", choices=MODES, default=list(MODES))
    parser.add_argument("--embedder", choices=["sentence-transformer", "hashing"], default="sentence-transformer")
    parser.add_argument("--embedder-model", default="BAAI/bge-base-en-v1.5")
    parser.add_argument("--no-cache", action="store_true", help="bypass the on-disk embedding cache")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = time.strftime("%Y%m%d-%H%M%S")

    if args.embedder == "sentence-transformer":
        embedder = SentenceTransformerEmbedder(args.embedder_model)
        if not args.no_cache:
            embedder = CachedEmbedder(embedder)
        label = args.embedder_model
    else:
        embedder, label = HashingEmbedder(), "hashing placeholder"
    print(f"embedder: {label}", flush=True)

    per_seed: list[dict] = []
    for nodes_per_corpus in args.nodes_per_corpus:
        for seed in args.seeds:
            tier_started = time.perf_counter()
            node_docs, queries, relevant_nodes, dropped = build_dataset(
                args.corpora, args.n_queries_per_corpus, args.docs_per_node,
                nodes_per_corpus, seed, allow_missing_docs=True,
            )
            docs_per_source = float(np.mean([len(v) for v in node_docs.values()]))
            profiles = build_node_profiles(node_docs, embedder, k=3, seed=seed)
            raw = embedder.embed([queries[qid] for qid in queries])
            query_vectors = {qid: _normalise(vec) for qid, vec in zip(queries, raw)}
            print(f"tier {nodes_per_corpus}/corpus seed {seed}: {len(node_docs)} sources, "
                  f"{docs_per_source:.1f} docs/source, {len(queries)} queries ({dropped} dropped), "
                  f"prepared in {time.perf_counter() - tier_started:.0f}s", flush=True)
            for mode in args.modes:
                row = run_mode_at_scale(
                    mode, profiles, queries, query_vectors, relevant_nodes,
                    max_nodes=args.max_nodes, genuine_k=args.genuine_k, coarse_k=args.coarse_k, seed=seed,
                )
                row.update({"seed": seed, "nodes_per_corpus": nodes_per_corpus,
                            "docs_per_source": docs_per_source, "dropped_queries": dropped})
                per_seed.append(row)
                print(f"  {mode:<9} recall {row['source_recall']:.3f} contacts {row['contacts']:.2f} "
                      f"latency {row['routing_latency_ms']:.2f}ms bytes {row['request_bytes']:.0f}", flush=True)
            # Checkpoint after every tier/seed so a long run that dies still leaves data.
            _write(RESULTS_DIR / f"scaling_{run_id}_per_seed.csv", per_seed)

    metrics = ("source_recall", "contacts", "audit_cost", "a2_precision", "a2_topics",
               "routing_latency_ms", "routing_latency_p95_ms", "request_bytes", "docs_per_source")
    summary: list[dict] = []
    for key in dict.fromkeys((r["nodes_per_corpus"], r["mode"]) for r in per_seed):
        group = [r for r in per_seed if (r["nodes_per_corpus"], r["mode"]) == key]
        entry = {"nodes_per_corpus": key[0], "sources": group[0]["sources"], "mode": key[1],
                 "seeds": len(group), "queries": int(np.mean([r["queries"] for r in group]))}
        for metric in metrics:
            values = [r[metric] for r in group]
            entry[f"{metric}_mean"] = float(np.nanmean(values))
            entry[f"{metric}_min"] = float(np.nanmin(values))
            entry[f"{metric}_max"] = float(np.nanmax(values))
        summary.append(entry)

    out = RESULTS_DIR / f"scaling_{run_id}.csv"
    _write(out, summary)
    print(json.dumps(summary, indent=2))
    print(f"wrote {out}")


def _write(path, rows: list[dict]) -> None:
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
