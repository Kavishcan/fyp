"""E3/E4 for the v2 decoy exemption (docs/30, docs/05-experiments.md).

E3 asks whether exempting decoy contacts from trust updates stops honest
decoys being penalised. E4 asks the harder question: the exemption is itself
observable — a node that is contacted but whose trust never moves was a decoy —
so does fixing E1 simply move the leak?

Three observers run against the SAME dispatch stream, so the numbers are
directly comparable:

- `frequency`: the A2 baseline. Sees only which sources were contacted per
  topic and guesses the most frequently contacted (attacks/a2_source_inference.py).
- `exemption`: sees dispatch sets AND which sources' trust values changed after
  each query. Guesses that contacted-but-unchanged means decoy. This is the E4
  attacker and it is deliberately strong — it is handed the exact side channel
  the E3 fix creates.
- `unmodified`: the E1 control, decoy exemption OFF, so trust moves for every
  contact. The exemption observer has nothing to exploit here by construction.

Reported: per-query decoy-identification precision/recall for each observer,
plus mean trust of decoy-role versus genuine-role sources.

Real BEIR data via eval.sweep.build_dataset; hashing encoder by default because
this measures a routing/trust mechanism, not retrieval quality. Nothing here
establishes a privacy guarantee: it measures one specific attacker against one
specific configuration.

Run: python -m eval.run_v2_interference
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import time

import numpy as np

from attacks.a2_source_inference import SourceInferenceObserver
from eval.sweep import (
    RESULTS_DIR,
    HashingEmbedder,
    SentenceTransformerEmbedder,
    _normalise,
    build_dataset,
    build_node_profiles,
)
from router.v2 import DecoyAwareEvidenceTrust, V2Config, select_dispatch


def _topic_key(relevant: set[str]) -> str:
    return "|".join(sorted(relevant)) if relevant else "unknown"


def _prf(guessed: set[str], truth: set[str]) -> tuple[float, float]:
    if not guessed:
        return (0.0, 0.0 if truth else 1.0)
    hits = len(guessed & truth)
    precision = hits / len(guessed)
    recall = hits / len(truth) if truth else 1.0
    return (precision, recall)


def run_condition(
    profiles: dict,
    node_docs: dict[str, list[str]],
    query_vectors: dict[str, np.ndarray],
    relevant_nodes: dict[str, set[str]],
    embedder,
    *,
    decoy_aware: bool,
    config: V2Config,
    seed: int,
) -> dict:
    trust_store = DecoyAwareEvidenceTrust()
    doc_embeddings = {nid: embedder.embed(texts) for nid, texts in node_docs.items()}
    query_ids = list(query_vectors)
    random.Random(seed).shuffle(query_ids)

    frequency_observer = SourceInferenceObserver()
    topic_truth: dict[str, set[str]] = {}
    topic_counts: dict[str, int] = {}

    exemption_scores, frequency_scores = [], []
    decoy_roles: dict[str, int] = {}
    genuine_roles: dict[str, int] = {}

    for qid in query_ids:
        query_vec = query_vectors[qid]
        relevant = relevant_nodes[qid]
        topic_key = _topic_key(relevant)

        decision = select_dispatch(
            query_vec, list(profiles.values()),
            trust={sid: trust_store.get(sid)[0] for sid in profiles},
            per_source_cost={sid: 1.0 for sid in profiles},
            topic_key=topic_key, config=config,
        )
        dispatched = decision.dispatched_source_ids
        if not dispatched:
            continue
        decoys = set(decision.decoy_source_ids)
        for sid in decoys:
            decoy_roles[sid] = decoy_roles.get(sid, 0) + 1
        for sid in decision.genuine_source_ids:
            genuine_roles[sid] = genuine_roles.get(sid, 0) + 1

        before = {sid: trust_store.get(sid) for sid in dispatched}
        for sid in dispatched:
            # Retrieval in the shared routing space, as v2 dispatch does.
            docs = doc_embeddings[sid]
            scores = docs @ query_vec
            top = docs[np.argsort(scores)[-1:]] if len(scores) else np.empty((0, 0))
            trust_store.observe(sid, profiles[sid], top, is_decoy=decoy_aware and sid in decoys)
        after = {sid: trust_store.get(sid) for sid in dispatched}

        # E4 attacker: contacted, but trust did not move -> guess decoy.
        exemption_guess = {sid for sid in dispatched if before[sid] == after[sid]}
        exemption_scores.append(_prf(exemption_guess, decoys))

        # A2 baseline attacker on the same dispatch set.
        frequency_observer.observe(topic_key, dispatched)
        topic_truth[topic_key] = relevant
        topic_counts[topic_key] = topic_counts.get(topic_key, 0) + 1
        inferred_genuine = set(frequency_observer.infer_topic_sources(topic_key, len(relevant)))
        frequency_scores.append(_prf(set(dispatched) - inferred_genuine, decoys))

    def mean_trust(roles: dict[str, int]) -> float:
        values = [trust_store.get(sid)[0] for sid in roles]
        return float(np.mean(values)) if values else float("nan")

    def mean_pair(scores):
        if not scores:
            return (float("nan"), float("nan"))
        return (float(np.mean([p for p, _ in scores])), float(np.mean([r for _, r in scores])))

    exemption_precision, exemption_recall = mean_pair(exemption_scores)
    frequency_precision, frequency_recall = mean_pair(frequency_scores)
    return {
        "condition": "e3_decoy_aware" if decoy_aware else "e1_unmodified",
        "queries": len(exemption_scores),
        "exemption_precision": exemption_precision,
        "exemption_recall": exemption_recall,
        "frequency_precision": frequency_precision,
        "frequency_recall": frequency_recall,
        "mean_trust_decoy_heavy": mean_trust({s: c for s, c in decoy_roles.items() if c > genuine_roles.get(s, 0)}),
        "mean_trust_genuine_heavy": mean_trust({s: c for s, c in genuine_roles.items() if c > decoy_roles.get(s, 0)}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpora", nargs="+", default=["arguana", "nfcorpus", "scifact"])
    parser.add_argument("--nodes-per-corpus", type=int, default=3)
    parser.add_argument("--docs-per-node", type=int, default=120)
    parser.add_argument("--n-queries-per-corpus", type=int, default=120)
    parser.add_argument("--max-nodes", type=int, default=6)
    parser.add_argument("--genuine-k", type=int, default=2)
    parser.add_argument("--coarse-k", type=int, default=9)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--embedder", choices=["hashing", "sentence-transformer"], default="hashing")
    parser.add_argument("--embedder-model", default="BAAI/bge-base-en-v1.5")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = time.strftime("%Y%m%d-%H%M%S")

    node_docs, queries, relevant_nodes, dropped = build_dataset(
        args.corpora, args.n_queries_per_corpus, args.docs_per_node, args.nodes_per_corpus, args.seed
    )
    print(f"{len(node_docs)} nodes, {len(queries)} queries ({dropped} dropped)")

    embedder = (
        SentenceTransformerEmbedder(args.embedder_model)
        if args.embedder == "sentence-transformer"
        else HashingEmbedder()
    )
    print(f"embedder: {args.embedder}"
          + ("" if args.embedder == "sentence-transformer" else " (placeholder encoder; mechanism test, not a retrieval result)"))

    profiles = {p.source_id: p for p in build_node_profiles(node_docs, embedder, k=3, seed=args.seed).values()}
    raw = embedder.embed([queries[qid] for qid in queries])
    query_vectors = {qid: _normalise(vec) for qid, vec in zip(queries, raw)}

    config = V2Config(
        exposure_budget=float(args.max_nodes), max_sources=args.max_nodes,
        genuine_k=args.genuine_k, coarse_k=args.coarse_k, aggregation="max",
    )

    rows = [
        run_condition(profiles, node_docs, query_vectors, relevant_nodes, embedder,
                      decoy_aware=False, config=config, seed=args.seed),
        run_condition(profiles, node_docs, query_vectors, relevant_nodes, embedder,
                      decoy_aware=True, config=config, seed=args.seed),
    ]

    out = RESULTS_DIR / f"v2_interference_{run_id}.csv"
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(json.dumps(rows, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
