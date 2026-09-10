"""A3 defence ablation for the v2 router (docs/32).

docs/30 shipped two A3-relevant controls without measuring either against an
actual hijacker: the publish-time plausibility check (router/registry.py) and
the runtime evidence trust (router/smart.EvidenceTrust). This measures both,
separately and together, so neither can be described as "an A3 defence" on the
strength of having been implemented.

Attacker: one source publishing a forged profile — the mean of the real query
distribution, the generic-attractor shape used by eval/run_attacks.py. Its
ACTUAL documents are an unrelated honest source's, so the profile lies about
content while retrieval behaviour stays honest (nodes/simulator.forge_profile).

Conditions:
- `none`         no plausibility check, trust frozen at the neutral prior.
- `plausibility` publish-time check only; if it rejects, the attacker never
                 registers and can never be selected.
- `trust`        runtime EvidenceTrust only; the attacker registers, is
                 selected, returns off-profile evidence and should decay.
- `both`         the shipped v2 configuration.

Reported per condition: attacker selection rate over the stream (first versus
last third, so suppression over time is visible), honest-source recall, and
whether honest sources were wrongly rejected at publish (collateral).

One attacker, one forgery strategy, one dataset family. A defence that stops
this specific generic-attractor shape is not shown to stop a targeted forgery.

Run: python -m eval.run_v2_a3
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import time

import numpy as np

from baselines.base import SourceProfile
from eval.sweep import (
    RESULTS_DIR,
    HashingEmbedder,
    SentenceTransformerEmbedder,
    _normalise,
    build_dataset,
    build_node_profiles,
)
from nodes.simulator import forge_profile
from router.registry import SourceRegistry
from router.smart import EvidenceTrust
from router.v2 import V2Config, select_dispatch

ATTACKER_ID = "attacker_forged"


def _topic_key(relevant: set[str]) -> str:
    return "|".join(sorted(relevant)) if relevant else "unknown"


def build_attacker(profiles: dict, query_vectors: dict[str, np.ndarray]) -> SourceProfile:
    """Generic attractor: a profile centred on the mean of all real queries."""
    mean_query = _normalise(np.mean(np.array(list(query_vectors.values())), axis=0))
    donor = next(iter(profiles.values()))
    attacker = forge_profile(donor, mean_query.reshape(1, -1))
    attacker.source_id = ATTACKER_ID
    return attacker


def run_condition(
    condition: str,
    profiles: dict,
    node_docs: dict[str, list[str]],
    query_vectors: dict[str, np.ndarray],
    relevant_nodes: dict[str, set[str]],
    embedder,
    *,
    config: V2Config,
    plausibility_threshold: float,
    seed: int,
) -> dict:
    use_plausibility = condition in {"plausibility", "both"}
    use_trust = condition in {"trust", "both"}

    registry = SourceRegistry(plausibility_threshold=plausibility_threshold if use_plausibility else None)
    honest_rejected = []
    for profile in profiles.values():
        try:
            registry.publish(profile)
        except ValueError:
            honest_rejected.append(profile.source_id)

    attacker = build_attacker(profiles, query_vectors)
    attacker_registered = True
    attacker_reject_reason = ""
    try:
        registry.publish(attacker)
    except ValueError as exc:
        attacker_registered = False
        attacker_reject_reason = str(exc).split(": ", 1)[-1]

    live = {p.source_id: p for p in registry.all_profiles()}
    # The attacker's real content is a donor's, so its evidence is off-profile.
    doc_embeddings = {nid: embedder.embed(texts) for nid, texts in node_docs.items()}
    doc_embeddings[ATTACKER_ID] = doc_embeddings[next(iter(node_docs))]

    trust_store = EvidenceTrust()
    query_ids = list(query_vectors)
    random.Random(seed).shuffle(query_ids)

    selected_flags, honest_hits = [], []
    for qid in query_ids:
        relevant = relevant_nodes[qid]
        decision = select_dispatch(
            query_vectors[qid], list(live.values()),
            trust={sid: (trust_store.get(sid)[0] if use_trust else 0.5) for sid in live},
            per_source_cost={sid: 1.0 for sid in live},
            topic_key=_topic_key(relevant), config=config,
        )
        dispatched = decision.dispatched_source_ids
        selected_flags.append(ATTACKER_ID in dispatched)
        honest_hits.append(1.0 if set(dispatched) & relevant else 0.0)

        if use_trust:
            for sid in dispatched:
                docs = doc_embeddings.get(sid)
                if docs is None or not len(docs):
                    continue
                scores = docs @ query_vectors[qid]
                trust_store.observe(sid, live[sid], docs[np.argsort(scores)[-1:]])

    third = max(1, len(selected_flags) // 3)
    return {
        "condition": condition,
        "queries": len(selected_flags),
        "attacker_registered": attacker_registered,
        "attacker_reject_reason": attacker_reject_reason,
        "attacker_selection_rate": float(np.mean(selected_flags)),
        "attacker_rate_first_third": float(np.mean(selected_flags[:third])),
        "attacker_rate_last_third": float(np.mean(selected_flags[-third:])),
        "attacker_final_trust": float(trust_store.get(ATTACKER_ID)[0]) if use_trust else float("nan"),
        "honest_mean_final_trust": (
            float(np.mean([trust_store.get(sid)[0] for sid in profiles])) if use_trust else float("nan")
        ),
        "honest_source_recall": float(np.mean(honest_hits)),
        "honest_sources_rejected_at_publish": len(honest_rejected),
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
    parser.add_argument("--plausibility-threshold", type=float, default=0.9)
    parser.add_argument("--minimum-trust", type=float, default=0.0,
                        help="v2 uses trust ONLY as an exclusion gate, so at 0.0 trust "
                             "cannot affect selection at all (see docs/32)")
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
        print(f"seed {seed}: {len(node_docs)} honest sources + 1 attacker, "
              f"{len(queries)} queries ({dropped} dropped)")
        profiles = build_node_profiles(node_docs, embedder, k=3, seed=seed)
        raw = embedder.embed([queries[qid] for qid in queries])
        query_vectors = {qid: _normalise(vec) for qid, vec in zip(queries, raw)}
        config = V2Config(
            exposure_budget=float(args.max_nodes), max_sources=args.max_nodes,
            genuine_k=args.genuine_k, coarse_k=args.coarse_k, aggregation="max",
            minimum_trust=args.minimum_trust,
        )
        for condition in ("none", "plausibility", "trust", "both"):
            row = run_condition(
                condition, profiles, node_docs, query_vectors, relevant_nodes, embedder,
                config=config, plausibility_threshold=args.plausibility_threshold, seed=seed,
            )
            row["seed"] = seed
            per_seed.append(row)

    numeric = ("attacker_selection_rate", "attacker_rate_first_third", "attacker_rate_last_third",
               "attacker_final_trust", "honest_mean_final_trust", "honest_source_recall",
               "honest_sources_rejected_at_publish")
    summary = []
    for condition in ("none", "plausibility", "trust", "both"):
        group = [r for r in per_seed if r["condition"] == condition]
        entry = {"condition": condition, "seeds": len(group), "queries": group[0]["queries"],
                 "attacker_registered": all(r["attacker_registered"] for r in group),
                 "attacker_reject_reason": next((r["attacker_reject_reason"] for r in group if r["attacker_reject_reason"]), "")}
        for metric in numeric:
            entry[f"{metric}_mean"] = float(np.nanmean([r[metric] for r in group]))
        summary.append(entry)

    raw_out = RESULTS_DIR / f"v2_a3_{run_id}_per_seed.csv"
    with raw_out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(per_seed[0]))
        writer.writeheader()
        writer.writerows(per_seed)
    out = RESULTS_DIR / f"v2_a3_{run_id}.csv"
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)

    print(json.dumps(summary, indent=2))
    print(f"wrote {out}\nwrote {raw_out}")


if __name__ == "__main__":
    main()
