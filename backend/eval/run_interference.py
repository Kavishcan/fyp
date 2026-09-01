"""E1 — decoy trust decay (docs/05-experiments.md "Interference experiments
(RQ03)"). The actual composition question: does this project's own privacy
layer (router/pipeline.py's PrivacyAwarePipeline, anonymity sets via
router/anonymity.py) survive being run on top of the real upstream TASR trust
defense (baselines/tasr_adapter.py)?

TASR's update_trust() has no concept of "this node was a decoy, not a real
answer" — it penalises a decoy-selected honest node's evidence exactly as it
would penalise a genuinely irrelevant one, because from TASR's point of view
every dispatched node was simply selected and returned mediocre evidence for
this query. This is the UNMODIFIED condition: no decoy exemption. Per
router/trust.py's own module docstring, this condition must exist and be
measured before any decoy-aware fix (E3, not built here) is compared against
it — CLAUDE.md's house rule against presenting a defended condition without
its baseline.

Prediction under test (docs/05-experiments.md E1): decoy-role nodes
accumulate lower TASR reputation than genuine-role nodes over a real query
stream, so the router increasingly avoids re-selecting them, the effective
anonymity set shrinks even though `m` is held constant, and A2 leakage
accuracy rises in the back half of the stream versus the front half.

Run: python -m eval.run_interference
"""
from __future__ import annotations

import argparse
import csv
import random
import time

import numpy as np

from attacks.a2_source_inference import SourceInferenceObserver, inference_accuracy
from baselines.tasr_adapter import TASRAdapter
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


def _topic_key(relevant: set[str]) -> str:
    return "|".join(sorted(relevant)) if relevant else "unknown"


def _make_feature_provider(profiles: dict, query_vec: np.ndarray):
    qn = _normalise(query_vec)

    def provider(candidate_ids):
        feats = {}
        for cid in candidate_ids:
            centroids = np.array([_normalise(c) for c in np.asarray(profiles[cid].centroids)])
            relevance = float(np.max(centroids @ qn)) if centroids.size else 0.0
            feats[cid] = RerankFeatures(
                relevance=relevance,
                trust=0.5,
                authorized=True,
                exposure_factors=ExposureFactors(0.0, 0.0, 0.0, 0.0),
                communication_cost=0.0,
                expected_latency=0.0,
                hijack_risk=0.0,
            )
        return feats

    return provider


def run_e1_decoy_trust_decay(
    profiles: dict,
    query_vectors: dict[str, np.ndarray],
    relevant_nodes: dict[str, set[str]],
    *,
    coarse_k: int,
    top_k: int,
    m: int,
    seed: int,
) -> dict:
    tasr = TASRAdapter()  # defense_mode="rel_cons_agr" default — UNMODIFIED, no decoy exemption
    tasr.register_sources(list(profiles.values()))
    pipeline = PrivacyAwarePipeline(tasr, rerank_weights=RerankWeights())
    rng = np.random.default_rng(seed)

    query_ids = list(query_vectors)
    random.Random(seed).shuffle(query_ids)
    n = len(query_ids)
    half = n // 2

    decoy_count = {nid: 0 for nid in profiles}
    genuine_count = {nid: 0 for nid in profiles}

    observer_first = SourceInferenceObserver()
    observer_second = SourceInferenceObserver()
    topic_gt_first: dict[str, set[str]] = {}
    topic_gt_second: dict[str, set[str]] = {}
    topic_occ_first: dict[str, int] = {}
    topic_occ_second: dict[str, int] = {}

    for i, qid in enumerate(query_ids):
        query_vec = query_vectors[qid]
        relevant = relevant_nodes[qid]
        topic_key = _topic_key(relevant)

        result = pipeline.route(
            query_vec,
            coarse_k=coarse_k,
            top_k=top_k,
            m=m,
            topic_key=topic_key,
            feature_provider=_make_feature_provider(profiles, query_vec),
            sigma=0.0,  # isolated from perturbation deliberately — this experiment is about the
            rng=rng,    # decoy/trust interaction alone, not conflated with query noise
        )

        for nid in result.genuine_source_ids:
            genuine_count[nid] += 1
        for nid in result.decoy_source_ids:
            decoy_count[nid] += 1

        tasr.update_trust(query_vec, result.dispatched_source_ids)  # unmodified: decoys fed back too

        observer = observer_first if i < half else observer_second
        topic_gt = topic_gt_first if i < half else topic_gt_second
        topic_occ = topic_occ_first if i < half else topic_occ_second
        observer.observe(topic_key, result.dispatched_source_ids)
        topic_gt[topic_key] = relevant
        topic_occ[topic_key] = topic_occ.get(topic_key, 0) + 1

    final_reputation = {tasr._id_to_source[cid]: rep for cid, rep in tasr._router.reputation.items()}

    decoy_heavy = [nid for nid in profiles if decoy_count[nid] > genuine_count[nid] and decoy_count[nid] > 0]
    genuine_heavy = [nid for nid in profiles if genuine_count[nid] > decoy_count[nid] and genuine_count[nid] > 0]

    def mean_rep(node_ids):
        return sum(final_reputation[nid] for nid in node_ids) / len(node_ids) if node_ids else float("nan")

    repeated_first = {k: v for k, v in topic_gt_first.items() if topic_occ_first.get(k, 0) >= 2}
    repeated_second = {k: v for k, v in topic_gt_second.items() if topic_occ_second.get(k, 0) >= 2}
    a2_first = inference_accuracy(observer_first, repeated_first) if repeated_first else {"mean": float("nan")}
    a2_second = inference_accuracy(observer_second, repeated_second) if repeated_second else {"mean": float("nan")}

    return {
        "n_queries": n,
        "decoy_heavy_node_count": len(decoy_heavy),
        "genuine_heavy_node_count": len(genuine_heavy),
        "mean_final_reputation_decoy_heavy": mean_rep(decoy_heavy),
        "mean_final_reputation_genuine_heavy": mean_rep(genuine_heavy),
        "a2_leakage_first_half": a2_first["mean"],
        "a2_leakage_second_half": a2_second["mean"],
        "a2_topics_first_half": len(repeated_first),
        "a2_topics_second_half": len(repeated_second),
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

    print("\n=== E1: decoy trust decay under real, unmodified TASR ===")
    result = run_e1_decoy_trust_decay(
        profiles, query_vectors, relevant_nodes,
        coarse_k=args.coarse_k, top_k=args.top_k, m=args.m, seed=args.seed,
    )
    out_csv = RESULTS_DIR / f"e1_decoy_trust_decay_{run_id}.csv"
    with out_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(result.keys()))
        writer.writeheader()
        writer.writerow(result)
    for k, v in result.items():
        print(f"  {k}: {v}")
    print(f"wrote {out_csv}")


if __name__ == "__main__":
    main()
