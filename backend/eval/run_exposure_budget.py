"""Exposure-budget sensitivity analysis (router/exposure.py) — the one
privacy-layer mechanism that has unit tests but had NEVER been exercised in a
real experiment before this script: every prior real run this session passed
`ExposureFactors(0, 0, 0, 0)` (inert) and never passed `exposure_budget` to
`PrivacyAwarePipeline.route()`. router/exposure.py's own module docstring:
"Every proxy, normalisation and weight must be reported and included in
sensitivity analysis; none of the defaults below are claimed to be correct
until measured."

Real (not fabricated) exposure factors, computed from the same real data
every other experiment this session used:

  - probability_source_is_irrelevant: 1 - this candidate's real cosine
    relevance, normalised within THIS query's own coarse-candidate pool.
  - query_specificity: 1 - normalised entropy of the similarity distribution
    across this query's real coarse candidates. A query whose similarity
    concentrates sharply on one node is more revealing to route at all than
    one spread evenly across many — a real, query-level exposure proxy.
  - route_linkability: running empirical frequency with which this exact
    node has actually been dispatched for this exact topic so far in the
    real 849-query stream — an observable repeat-pattern signal built from
    the stream itself, not assumed.
  - sensitive_token_fraction_sent: held at 0.0 and EXPLICITLY FLAGGED as not
    measured. No validated sensitive-term classifier exists for this dataset.
    Fabricating a number here would violate CLAUDE.md's "no fabricated or
    assumed empirical values" rule more than leaving a documented zero.

Two real analyses:
  1. Budget sweep — exposure_budget set at percentiles of the REAL observed
     no-budget dispatched-cost distribution (not arbitrary round numbers),
     confirming genuine sources stay protected and measuring what actually
     gets truncated as the budget tightens.
  2. Weight sensitivity — fixed tight budget, each of the three measured
     weights isolated in turn, to see which factor actually drives
     truncation decisions.

Run: python -m eval.run_exposure_budget
"""
from __future__ import annotations

import argparse
import csv
import random
import time
from collections import defaultdict

import numpy as np

from baselines.cosine_router import CosineRouter
from eval.metrics import recall_at_k
from eval.sweep import (
    RESULTS_DIR,
    HashingEmbedder,
    SentenceTransformerEmbedder,
    _normalise,
    build_dataset,
    build_node_profiles,
)
from router.exposure import ExposureFactors, ExposureWeights, exposure_cost
from router.pipeline import PrivacyAwarePipeline, RerankFeatures, RerankWeights


def compute_specificity(similarities: np.ndarray) -> float:
    """1 - normalised entropy of a query's similarity distribution across its
    real coarse candidates. Concentrated (low entropy) -> high specificity.
    """
    if len(similarities) <= 1:
        return 0.0
    shifted = similarities - similarities.min() + 1e-6
    probs = shifted / shifted.sum()
    entropy = -float(np.sum(probs * np.log(probs)))
    max_entropy = float(np.log(len(probs)))
    normalised_entropy = entropy / max_entropy if max_entropy > 0 else 0.0
    return 1.0 - normalised_entropy


def run_condition(
    profiles: dict,
    query_vectors: dict[str, np.ndarray],
    relevant_nodes: dict[str, set[str]],
    *,
    coarse_k: int,
    top_k: int,
    m: int,
    exposure_budget: float | None,
    exposure_weights: ExposureWeights,
    seed: int,
) -> dict:
    baseline = CosineRouter(aggregation="max")
    baseline.register_sources(list(profiles.values()))
    pipeline = PrivacyAwarePipeline(baseline, rerank_weights=RerankWeights())
    rng = np.random.default_rng(seed)

    selection_counts: dict[tuple[str, str], int] = defaultdict(int)
    topic_counts: dict[str, int] = defaultdict(int)

    query_ids = list(query_vectors)
    random.Random(seed).shuffle(query_ids)
    n = len(query_ids)

    recalls, dispatched_sizes, dispatched_costs = [], [], []

    for qid in query_ids:
        query_vec = query_vectors[qid]
        relevant = relevant_nodes[qid]
        topic_key = "|".join(sorted(relevant)) if relevant else "unknown"
        qn = _normalise(query_vec)

        last_feats: dict[str, RerankFeatures] = {}

        def feature_provider(candidate_ids, qn=qn, topic_key=topic_key, last_feats=last_feats):
            sims = {}
            for cid in candidate_ids:
                centroids = np.array([_normalise(c) for c in np.asarray(profiles[cid].centroids)])
                sims[cid] = float(np.max(centroids @ qn)) if centroids.size else 0.0
            sim_values = np.array(list(sims.values()))
            spec = compute_specificity(sim_values)
            max_sim, min_sim = float(sim_values.max()), float(sim_values.min())
            span = (max_sim - min_sim) or 1.0

            feats = {}
            for cid in candidate_ids:
                relevance = sims[cid]
                irrelevance = 1.0 - (relevance - min_sim) / span
                linkability = (
                    selection_counts[(topic_key, cid)] / topic_counts[topic_key]
                    if topic_counts[topic_key] > 0
                    else 0.0
                )
                feats[cid] = RerankFeatures(
                    relevance=relevance,
                    trust=0.5,
                    authorized=True,
                    exposure_factors=ExposureFactors(
                        sensitive_token_fraction_sent=0.0,  # NOT measured — see module docstring
                        query_specificity=spec,
                        probability_source_is_irrelevant=irrelevance,
                        route_linkability=linkability,
                    ),
                    communication_cost=0.0,
                    expected_latency=0.0,
                    hijack_risk=0.0,
                )
            last_feats.update(feats)
            return feats

        result = pipeline.route(
            query_vec,
            coarse_k=coarse_k,
            top_k=top_k,
            m=m,
            topic_key=topic_key,
            feature_provider=feature_provider,
            sigma=0.0,
            rng=rng,
            exposure_weights=exposure_weights,
            exposure_budget=exposure_budget,
        )

        topic_counts[topic_key] += 1
        for nid in result.dispatched_source_ids:
            selection_counts[(topic_key, nid)] += 1

        recalls.append(recall_at_k(result.genuine_source_ids, relevant))
        dispatched_sizes.append(len(result.dispatched_source_ids))
        dispatched_costs.append(
            sum(exposure_cost(last_feats[cid].exposure_factors, exposure_weights) for cid in result.dispatched_source_ids if cid in last_feats)
        )

    return {
        "n_queries": n,
        "mean_recall": sum(recalls) / n,
        "mean_nodes_contacted": sum(dispatched_sizes) / n,
        "mean_dispatched_exposure_cost": sum(dispatched_costs) / n,
        "raw_costs": dispatched_costs,  # kept for percentile calc, stripped before CSV write
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpora", nargs="+", default=["arguana", "nfcorpus", "scifact", "fiqa", "trec-covid", "scidocs", "webis-touche2020"])
    parser.add_argument("--nodes-per-corpus", type=int, default=3)
    parser.add_argument("--docs-per-node", type=int, default=150)
    parser.add_argument("--n-queries-per-corpus", type=int, default=150)
    parser.add_argument("--coarse-k", type=int, default=11)
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--m", type=int, default=6)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--embedder", choices=["sentence-transformer", "hashing"], default="sentence-transformer")
    parser.add_argument("--embedder-model", default="BAAI/bge-base-en-v1.5")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = time.strftime("%Y%m%d-%H%M%S")

    print(f"Loading {args.corpora}...")
    node_docs, queries, relevant_nodes, dropped = build_dataset(
        args.corpora, args.n_queries_per_corpus, args.docs_per_node, args.nodes_per_corpus, args.seed
    )
    print(f"{len(node_docs)} nodes, {len(queries)} queries ({dropped} dropped)")

    if args.embedder == "sentence-transformer":
        embedder = SentenceTransformerEmbedder(args.embedder_model)
        print(f"embedder: {args.embedder_model}")
    else:
        embedder = HashingEmbedder()
        print("embedder: hashing placeholder — NOT a reportable result")

    profiles = build_node_profiles(node_docs, embedder, k=3, seed=args.seed)

    print(f"embedding {len(queries)} queries...")
    query_ids = list(queries)
    raw_vectors = embedder.embed([queries[qid] for qid in query_ids])
    query_vectors = {qid: _normalise(vec) for qid, vec in zip(query_ids, raw_vectors)}

    default_weights = ExposureWeights()

    print("\n=== Pass 1: no budget — establishing the real cost distribution ===")
    no_budget = run_condition(
        profiles, query_vectors, relevant_nodes,
        coarse_k=args.coarse_k, top_k=args.top_k, m=args.m,
        exposure_budget=None, exposure_weights=default_weights, seed=args.seed,
    )
    costs = sorted(no_budget["raw_costs"])
    p50 = costs[len(costs) // 2]
    p25 = costs[len(costs) // 4]
    p10 = costs[len(costs) // 10]
    print(f"  observed dispatched-cost percentiles: p50={p50:.3f} p25={p25:.3f} p10={p10:.3f}")

    print("\n=== 1. Budget sweep (real percentile-derived budgets) ===")
    budget_rows = []
    for label, budget in [("none", None), ("p50", p50), ("p25", p25), ("p10", p10)]:
        row = run_condition(
            profiles, query_vectors, relevant_nodes,
            coarse_k=args.coarse_k, top_k=args.top_k, m=args.m,
            exposure_budget=budget, exposure_weights=default_weights, seed=args.seed,
        )
        row.pop("raw_costs")
        row["budget_label"] = label
        row["budget_value"] = budget if budget is not None else "none"
        budget_rows.append(row)
        print(f"  budget={label} ({row['budget_value']}): recall={row['mean_recall']:.3f} "
              f"nodes_contacted={row['mean_nodes_contacted']:.3f} "
              f"dispatched_cost={row['mean_dispatched_exposure_cost']:.3f}")

    budget_csv = RESULTS_DIR / f"exposure_budget_sweep_{run_id}.csv"
    with budget_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(budget_rows[0].keys()))
        writer.writeheader()
        writer.writerows(budget_rows)
    print(f"wrote {budget_csv}")

    print("\n=== 2. Weight sensitivity (fixed tight budget = p25) ===")
    weight_configs = {
        "all_default_1.0": ExposureWeights(),
        "specificity_only": ExposureWeights(sensitive_token_fraction=0.0, query_specificity=1.0, irrelevance_probability=0.0, route_linkability=0.0),
        "irrelevance_only": ExposureWeights(sensitive_token_fraction=0.0, query_specificity=0.0, irrelevance_probability=1.0, route_linkability=0.0),
        "linkability_only": ExposureWeights(sensitive_token_fraction=0.0, query_specificity=0.0, irrelevance_probability=0.0, route_linkability=1.0),
    }
    sensitivity_rows = []
    for name, weights in weight_configs.items():
        row = run_condition(
            profiles, query_vectors, relevant_nodes,
            coarse_k=args.coarse_k, top_k=args.top_k, m=args.m,
            exposure_budget=p25, exposure_weights=weights, seed=args.seed,
        )
        row.pop("raw_costs")
        row["weight_config"] = name
        sensitivity_rows.append(row)
        print(f"  {name}: recall={row['mean_recall']:.3f} nodes_contacted={row['mean_nodes_contacted']:.3f} "
              f"dispatched_cost={row['mean_dispatched_exposure_cost']:.3f}")

    sensitivity_csv = RESULTS_DIR / f"exposure_weight_sensitivity_{run_id}.csv"
    with sensitivity_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(sensitivity_rows[0].keys()))
        writer.writeheader()
        writer.writerows(sensitivity_rows)
    print(f"wrote {sensitivity_csv}")


if __name__ == "__main__":
    main()
