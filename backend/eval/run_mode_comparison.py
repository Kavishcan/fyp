"""Matched-budget comparison of legacy, smart and v2 routing (docs/31).

The gap docs/30 left open: v2 was built and unit-tested but never compared
against the modes it is meant to improve on. This runs all three over the SAME
sources, queries, seed and contact budget, and reports utility, cost and A2
leakage together — a privacy mechanism that wins on leakage by contacting
fewer relevant sources has not won anything, so the three must be read jointly.

Conditions (all capped at the same `--max-nodes` contacts):

- `legacy`   router/pipeline.PrivacyAwarePipeline: perturbed routing, genuine
             set exempt from the exposure budget, topic-stable decoys on top.
- `smart`    router/smart.SmartRouter: strict budget, NO decoys, no perturbation.
- `v2`       router/v2.select_dispatch: unperturbed local routing, one budget
             covering genuine and decoys, topic-stable decoys.
- `broadcast`/`oracle`: contact-everything and qrel-perfect reference bounds.

Metrics per condition:
- source_recall     fraction of queries whose dispatched set contained a
                    genuinely relevant source (utility).
- contacts          mean sources contacted (cost/exposure).
- audit_cost        mean contacted sources with no relevant content.
- a2_precision      the A2 observer's precision at naming the genuine sources
                    for a topic from dispatch patterns alone (leakage; lower is
                    better). attacks/a2_source_inference.py, same attacker for
                    every condition.

Not a privacy guarantee and not a general ranking of the three designs: one
dataset family, one attacker, one budget policy, fixed seed. `sigma` applies
only where the mode supports it (legacy perturbs routing; v2 perturbs the
dispatched vector, which does not change these metrics; smart rejects it).

Run: python -m eval.run_mode_comparison
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import time

import numpy as np

from attacks.a2_source_inference import SourceInferenceObserver
from baselines.cosine_router import CosineRouter
from eval.sweep import (
    RESULTS_DIR,
    HashingEmbedder,
    SentenceTransformerEmbedder,
    _normalise,
    build_dataset,
    build_node_profiles,
)
from router.exposure import ExposureFactors
from router.pipeline import PrivacyAwarePipeline, RerankFeatures, RerankWeights
from router.smart import SmartConfig, SmartRouter, SourceEvidence
from router.v2 import V2Config, select_dispatch


def _topic_key(relevant: set[str]) -> str:
    return "|".join(sorted(relevant)) if relevant else "unknown"


def _legacy_feature_provider(profiles: dict, query_vec: np.ndarray):
    def provider(candidate_ids):
        features = {}
        for cid in candidate_ids:
            centroids = _normalise_rows(np.asarray(profiles[cid].centroids, dtype=np.float64))
            relevance = float(np.max(centroids @ _normalise(query_vec)))
            features[cid] = RerankFeatures(
                relevance=relevance, trust=0.5, authorized=True,
                exposure_factors=ExposureFactors(0.0, 0.0, 0.0, 0.0),
                communication_cost=0.0, expected_latency=0.0, hijack_risk=0.0,
            )
        return features

    return provider


def _normalise_rows(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return np.divide(matrix, norms, out=np.zeros_like(matrix), where=norms != 0)


def dispatch_for_mode(
    mode: str,
    query_vec: np.ndarray,
    profiles: dict,
    topic_key: str,
    relevant: set[str],
    *,
    max_nodes: int,
    genuine_k: int,
    coarse_k: int,
    sigma: float,
    rng: np.random.Generator,
) -> list[str]:
    profile_list = list(profiles.values())
    if mode == "broadcast":
        return [p.source_id for p in profile_list]
    if mode == "oracle":
        return sorted(relevant)[:max_nodes]
    if mode == "v2":
        decision = select_dispatch(
            query_vec, profile_list,
            trust={sid: 0.5 for sid in profiles},
            per_source_cost={sid: 1.0 for sid in profiles},
            topic_key=topic_key,
            config=V2Config(
                exposure_budget=float(max_nodes), max_sources=max_nodes,
                genuine_k=genuine_k, coarse_k=coarse_k, aggregation="max",
            ),
        )
        return decision.dispatched_source_ids
    if mode == "smart":
        evidence = {sid: SourceEvidence(trust=0.5, observations=0, authorized=True, exposure_cost=1.0)
                    for sid in profiles}
        decision = SmartRouter().route(
            query_vec, profile_list, evidence,
            SmartConfig(exposure_budget=float(max_nodes), max_sources=max_nodes,
                        minimum_gain=0.0, aggregation="max"),
        )
        return decision.selected_source_ids
    if mode == "legacy":
        baseline = CosineRouter(aggregation="max")
        baseline.register_sources(profile_list)
        pipeline = PrivacyAwarePipeline(baseline, RerankWeights())
        result = pipeline.route(
            query_vec, coarse_k=coarse_k, top_k=genuine_k, m=max_nodes,
            topic_key=topic_key, feature_provider=_legacy_feature_provider(profiles, query_vec),
            sigma=sigma, rng=rng,
        )
        return result.dispatched_source_ids
    raise ValueError(f"unknown mode {mode!r}")


def run_mode(
    mode: str,
    profiles: dict,
    query_vectors: dict[str, np.ndarray],
    relevant_nodes: dict[str, set[str]],
    *,
    max_nodes: int,
    genuine_k: int,
    coarse_k: int,
    sigma: float,
    seed: int,
) -> dict:
    rng = np.random.default_rng(seed)
    query_ids = list(query_vectors)
    random.Random(seed).shuffle(query_ids)

    observer = SourceInferenceObserver()
    topic_truth: dict[str, set[str]] = {}
    topic_counts: dict[str, int] = {}

    hits, contacts, audit = [], [], []
    for qid in query_ids:
        relevant = relevant_nodes[qid]
        topic_key = _topic_key(relevant)
        dispatched = dispatch_for_mode(
            mode, query_vectors[qid], profiles, topic_key, relevant,
            max_nodes=max_nodes, genuine_k=genuine_k, coarse_k=coarse_k, sigma=sigma, rng=rng,
        )
        hits.append(1.0 if set(dispatched) & relevant else 0.0)
        contacts.append(len(dispatched))
        audit.append(len([s for s in dispatched if s not in relevant]))
        observer.observe(topic_key, dispatched)
        topic_truth[topic_key] = relevant
        topic_counts[topic_key] = topic_counts.get(topic_key, 0) + 1

    # A2: only topics seen more than once give the observer anything to correlate.
    precisions = []
    for topic_key, truth in topic_truth.items():
        if topic_counts[topic_key] < 2 or not truth:
            continue
        guess = set(observer.infer_topic_sources(topic_key, len(truth)))
        if guess:
            precisions.append(len(guess & truth) / len(guess))

    return {
        "mode": mode,
        "sigma": sigma,
        "queries": len(query_ids),
        "source_recall": float(np.mean(hits)),
        "contacts": float(np.mean(contacts)),
        "audit_cost": float(np.mean(audit)),
        "a2_precision": float(np.mean(precisions)) if precisions else float("nan"),
        "a2_topics": len(precisions),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpora", nargs="+", default=["arguana", "nfcorpus", "scifact"])
    parser.add_argument("--nodes-per-corpus", type=int, default=4)
    parser.add_argument("--docs-per-node", type=int, default=120)
    parser.add_argument("--n-queries-per-corpus", type=int, default=150)
    parser.add_argument("--max-nodes", type=int, default=6)
    parser.add_argument("--genuine-k", type=int, default=2)
    parser.add_argument("--coarse-k", type=int, default=12)
    parser.add_argument("--sigmas", nargs="+", type=float, default=[0.0, 0.25, 1.0])
    parser.add_argument("--seeds", nargs="+", type=int, default=[11, 22, 33],
                        help="each seed repartitions sources and reshuffles the stream; "
                             "results are reported as mean [min, max] across seeds")
    parser.add_argument("--embedder", choices=["sentence-transformer", "hashing"], default="sentence-transformer")
    parser.add_argument("--embedder-model", default="BAAI/bge-base-en-v1.5")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = time.strftime("%Y%m%d-%H%M%S")

    embedder = (
        SentenceTransformerEmbedder(args.embedder_model)
        if args.embedder == "sentence-transformer"
        else HashingEmbedder()
    )
    print(f"embedder: {args.embedder_model if args.embedder == 'sentence-transformer' else 'hashing placeholder'}")

    per_seed_rows: list[dict] = []
    for seed in args.seeds:
        # Tolerant of BEIR qrels pointing at absent doc ids, which otherwise
        # makes a run's success depend on which queries the seed sampled.
        # Dropped queries are reported per seed, not silently discarded.
        node_docs, queries, relevant_nodes, dropped = build_dataset(
            args.corpora, args.n_queries_per_corpus, args.docs_per_node, args.nodes_per_corpus, seed,
            allow_missing_docs=True,
        )
        print(f"seed {seed}: {len(node_docs)} sources, {len(queries)} queries "
              f"({dropped} dropped), cap {args.max_nodes} contacts")

        profiles = build_node_profiles(node_docs, embedder, k=3, seed=seed)
        raw = embedder.embed([queries[qid] for qid in queries])
        query_vectors = {qid: _normalise(vec) for qid, vec in zip(queries, raw)}

        common = dict(max_nodes=args.max_nodes, genuine_k=args.genuine_k,
                      coarse_k=args.coarse_k, seed=seed)
        for mode in ("broadcast", "oracle", "smart", "v2"):
            per_seed_rows.append(run_mode(mode, profiles, query_vectors, relevant_nodes, sigma=0.0, **common))
        for sigma in args.sigmas:
            per_seed_rows.append(run_mode("legacy", profiles, query_vectors, relevant_nodes, sigma=sigma, **common))

    # Aggregate across seeds. Seeds share documents and questions, so these are
    # repeated partitions of the same data, NOT independent query samples —
    # the spread shows partition sensitivity, not a confidence interval.
    metrics = ("source_recall", "contacts", "audit_cost", "a2_precision")
    summary: list[dict] = []
    for key in dict.fromkeys((row["mode"], row["sigma"]) for row in per_seed_rows):
        group = [r for r in per_seed_rows if (r["mode"], r["sigma"]) == key]
        entry = {"mode": key[0], "sigma": key[1], "seeds": len(group), "queries": group[0]["queries"]}
        for metric in metrics:
            values = [r[metric] for r in group]
            entry[f"{metric}_mean"] = float(np.mean(values))
            entry[f"{metric}_min"] = float(np.min(values))
            entry[f"{metric}_max"] = float(np.max(values))
        summary.append(entry)

    raw_out = RESULTS_DIR / f"mode_comparison_{run_id}_per_seed.csv"
    with raw_out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(per_seed_rows[0]))
        writer.writeheader()
        writer.writerows(per_seed_rows)

    out = RESULTS_DIR / f"mode_comparison_{run_id}.csv"
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)

    print(json.dumps(summary, indent=2))
    print(f"wrote {out}")
    print(f"wrote {raw_out}")


if __name__ == "__main__":
    main()
