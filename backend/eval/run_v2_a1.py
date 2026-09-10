"""A1 residual-inversion measurement for v2 dispatch (docs/32).

docs/30 states that v2's shared-space dispatch vector "can still be inverted
toward the query" and is therefore not query secrecy. That was an assertion.
This measures it: how much of the query does a node actually recover from the
vector v2 sends, and what does raising `sigma` cost in retrieval quality?

The attacker is attacks/a1_inversion.NearestNeighbourInversion — a transparent
nearest-neighbour baseline against a reference corpus of real queries, not a
trained inversion model. It establishes a floor, so the recovery figures here
are a lower bound on what a stronger attacker could achieve.

Utility here is DOCUMENT-level, not routing-level: in v2, sigma perturbs only
the dispatched vector, so it cannot change which sources are contacted. It
changes what those sources retrieve. Reporting routing recall against sigma
would show a flat line and hide the real cost.

The utility metric is `retrieval_agreement`: for each contacted source, does
its top-1 document under the perturbed vector match the one it would have
returned unperturbed? That measures exactly what the noise costs, and needs no
document-level qrels — which `build_dataset` does not expose. It is not a
relevance measure: agreement with the sigma-0 result says the noise changed
nothing, not that the unperturbed answer was correct.

Run: python -m eval.run_v2_a1
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import time

import numpy as np

from attacks.a1_inversion import NearestNeighbourInversion, term_recovery_rate
from eval.sweep import (
    RESULTS_DIR,
    HashingEmbedder,
    SentenceTransformerEmbedder,
    _normalise,
    build_dataset,
    build_node_profiles,
)
from router.v2 import V2Config, dispatched_vector, select_dispatch


def _topic_key(relevant: set[str]) -> str:
    return "|".join(sorted(relevant)) if relevant else "unknown"


def run_sigma(
    sigma: float,
    profiles: dict,
    doc_embeddings: dict[str, np.ndarray],
    query_vectors: dict[str, np.ndarray],
    query_texts: dict[str, str],
    relevant_nodes: dict[str, set[str]],
    *,
    config: V2Config,
    seed: int,
) -> dict:
    rng = np.random.default_rng(seed)
    query_ids = list(query_vectors)
    random.Random(seed).shuffle(query_ids)

    # The attacker's reference corpus is the real query pool: given the vector,
    # name which of the plausible queries produced it.
    inverter = NearestNeighbourInversion(
        [query_texts[qid] for qid in query_ids],
        np.array([query_vectors[qid] for qid in query_ids]),
    )

    term_rates, exact_hits, agreements = [], 0, []
    for qid in query_ids:
        query_vec = query_vectors[qid]
        relevant = relevant_nodes[qid]
        decision = select_dispatch(
            query_vec, list(profiles.values()),
            trust={sid: 0.5 for sid in profiles},
            per_source_cost={sid: 1.0 for sid in profiles},
            topic_key=_topic_key(relevant), config=config,
        )
        sent = dispatched_vector(query_vec, sigma, rng)

        recovered = inverter.recover(sent)
        term_rates.append(term_recovery_rate(recovered, query_texts[qid]))
        exact_hits += int(recovered == query_texts[qid])

        # Utility: does each contacted source still return the document it
        # would have returned without noise?
        for sid in decision.dispatched_source_ids:
            docs = doc_embeddings.get(sid)
            if docs is None or not len(docs):
                continue
            agreements.append(
                1.0 if int(np.argmax(docs @ sent)) == int(np.argmax(docs @ query_vec)) else 0.0
            )

    n = len(query_ids)
    return {
        "sigma": sigma,
        "queries": n,
        "a1_term_recovery": float(np.mean(term_rates)),
        "a1_exact_recovery": exact_hits / n,
        "retrieval_agreement": float(np.mean(agreements)) if agreements else float("nan"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpora", nargs="+", default=["arguana", "nfcorpus", "scifact"])
    parser.add_argument("--nodes-per-corpus", type=int, default=8)
    parser.add_argument("--docs-per-node", type=int, default=120)
    parser.add_argument("--n-queries-per-corpus", type=int, default=150)
    parser.add_argument("--max-nodes", type=int, default=6)
    parser.add_argument("--genuine-k", type=int, default=2)
    parser.add_argument("--coarse-k", type=int, default=12)
    parser.add_argument("--sigmas", nargs="+", type=float, default=[0.0, 0.1, 0.25, 0.5, 1.0])
    parser.add_argument("--seeds", nargs="+", type=int, default=[11, 22, 33])
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

    per_seed: list[dict] = []
    for seed in args.seeds:
        node_docs, queries, relevant_nodes, dropped = build_dataset(
            args.corpora, args.n_queries_per_corpus, args.docs_per_node,
            args.nodes_per_corpus, seed, allow_missing_docs=True,
        )
        print(f"seed {seed}: {len(node_docs)} sources, {len(queries)} queries ({dropped} dropped)")
        profiles = build_node_profiles(node_docs, embedder, k=3, seed=seed)
        raw = embedder.embed([queries[qid] for qid in queries])
        query_vectors = {qid: _normalise(vec) for qid, vec in zip(queries, raw)}
        doc_embeddings = {nid: embedder.embed(texts) for nid, texts in node_docs.items()}

        config = V2Config(
            exposure_budget=float(args.max_nodes), max_sources=args.max_nodes,
            genuine_k=args.genuine_k, coarse_k=args.coarse_k, aggregation="max",
        )
        for sigma in args.sigmas:
            row = run_sigma(
                sigma, profiles, doc_embeddings, query_vectors, queries,
                relevant_nodes, config=config, seed=seed,
            )
            row["seed"] = seed
            per_seed.append(row)

    metrics = ("a1_term_recovery", "a1_exact_recovery", "retrieval_agreement")
    summary = []
    for sigma in args.sigmas:
        group = [r for r in per_seed if r["sigma"] == sigma]
        entry = {"sigma": sigma, "seeds": len(group), "queries": group[0]["queries"]}
        for metric in metrics:
            values = [r[metric] for r in group]
            entry[f"{metric}_mean"] = float(np.mean(values))
            entry[f"{metric}_min"] = float(np.min(values))
            entry[f"{metric}_max"] = float(np.max(values))
        summary.append(entry)

    raw_out = RESULTS_DIR / f"v2_a1_{run_id}_per_seed.csv"
    with raw_out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(per_seed[0]))
        writer.writeheader()
        writer.writerows(per_seed)
    out = RESULTS_DIR / f"v2_a1_{run_id}.csv"
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)

    print(json.dumps(summary, indent=2))
    print(f"wrote {out}\nwrote {raw_out}")


if __name__ == "__main__":
    main()
