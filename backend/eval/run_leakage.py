"""The routing-privacy table (docs/39): does the dispatch pattern leak the
query topic, and what do decoys do about it?

Runs the routing conditions the review ladder asks for on FeB4RAG, with the
query's ORIGIN ENGINE as its topic label (13 classes) and the engine's
vertical as a coarser label (6 classes), and measures per condition:

Leakage
- topic attack   attacks/a2_topic_inference: a learned observer (naive Bayes
                 on multi-hot contact vectors, trained on half the labelled
                 history, tested on the other half) and the metadata-only
                 floor (guess a contacted source's domain). Accuracy,
                 macro-F1, top-3, chance.
- source attack  attacks/a2_source_inference precision at naming the origin
                 engine from the per-topic contact counts (the docs/31 A2).
- decoy stability  mean Jaccard between the decoy sets of same-topic queries.

Utility and cost
- best-engine contacted, graded captured gain (eval/run_feb4rag), contacts,
  contacts that are not the origin engine.

Conditions (cap K contacts unless stated)
- random         RandomRouter top-K — lower bound.
- broadcast      every engine — pattern carries no information.
- cosine@g       plain cosine top-genuine_k, no decoys — the "normal router".
- cosine@K       plain cosine top-K, no decoys — normal router at equal fan-out.
- sticky_decoys  v2 select_dispatch: genuine_k + topic-stable decoys from the
                 coarse pool; the pattern psi mode produces.
- random_decoys  genuine_k + fresh random decoys from the coarse pool.
- random_any     genuine_k + fresh random decoys from ALL engines.
- oracle         the best-graded engine(s).

The topic key for sticky decoys is the live api/topic.assign_topic_key
(nearest published centroid), not the ground-truth label, so stickiness is
what an observer would actually face.

Run: python -m eval.run_leakage
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import time
from collections import defaultdict

import numpy as np

from api.topic import assign_topic_key
from attacks.a2_source_inference import SourceInferenceObserver
from attacks.a2_topic_inference import HistoryAttacker, SetPriorAttacker, evaluate, jaccard
from baselines.cosine_router import CosineRouter
from baselines.random_router import RandomRouter
from eval.embed_cache import CachedEmbedder
from eval.run_feb4rag import FEB4RAG_DIR, available_engines, captured_gain, load_requests, load_rs_qrels, sample_corpus
from eval.sweep import RESULTS_DIR, HashingEmbedder, SentenceTransformerEmbedder, _normalise, build_node_profiles
from router.anonymity import random_sample, topic_stable_sample
from router.v2 import V2Config, select_dispatch

CONDITIONS = ("random", "broadcast", "cosine@g", "cosine@K", "sticky_decoys", "random_decoys", "random_any", "oracle")


def load_origin(engines: set[str]) -> dict[str, str]:
    """request id -> origin engine (FeB4RAG rid_mapping.tsv)."""
    out = {}
    with (FEB4RAG_DIR / "queries" / "rid_mapping.tsv").open() as handle:
        for line in handle:
            rid, engine, _ = line.rstrip("\n").split("\t")
            if engine in engines:
                out[rid] = engine
    return out


def load_verticals() -> dict[str, str]:
    with (FEB4RAG_DIR / "engines" / "engines.csv").open() as handle:
        return {row["name"]: row["vertical"] for row in csv.DictReader(handle)}


def dispatch(condition: str, vec, profiles: dict, grades: dict, *, max_nodes: int, genuine_k: int,
             coarse_k: int, rng: random.Random, random_router: RandomRouter) -> tuple[list[str], list[str]]:
    """Returns (dispatched, decoys)."""
    ids = list(profiles)
    if condition == "broadcast":
        return ids, []
    if condition == "random":
        return random_router.rank(vec, top_k=max_nodes).ranked_source_ids, []
    if condition == "oracle":
        best = max(grades.values())
        return sorted(e for e, g in grades.items() if g == best)[:max_nodes], []
    router = CosineRouter(aggregation="max")
    router.register_sources(list(profiles.values()))
    ranking = list(router.rank(vec, top_k=coarse_k).ranked_source_ids)
    if condition == "cosine@g":
        return ranking[:genuine_k], []
    if condition == "cosine@K":
        return ranking[:max_nodes], []
    genuine = ranking[:genuine_k]
    needed = max_nodes - len(genuine)
    if condition == "sticky_decoys":
        decision = select_dispatch(vec, list(profiles.values()), trust={e: 0.5 for e in ids},
                                   per_source_cost={e: 1.0 for e in ids},
                                   topic_key=assign_topic_key(vec, list(profiles.values())),
                                   config=V2Config(exposure_budget=float(max_nodes), max_sources=max_nodes,
                                                   genuine_k=genuine_k, coarse_k=coarse_k, aggregation="max"))
        return decision.dispatched_source_ids, decision.decoy_source_ids
    pool = [e for e in (ranking if condition == "random_decoys" else ids) if e not in genuine]
    decoys = random_sample(pool, min(needed, len(pool)), rng)
    dispatched = [*genuine, *decoys]
    rng.shuffle(dispatched)
    return dispatched, decoys


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--docs-per-engine", type=int, default=1500)
    parser.add_argument("--scan-lines", type=int, default=200_000)
    parser.add_argument("--max-nodes", type=int, default=4)
    parser.add_argument("--genuine-k", type=int, default=2)
    parser.add_argument("--coarse-k", type=int, default=8)
    parser.add_argument("--seeds", nargs="+", type=int, default=[11, 22, 33])
    parser.add_argument("--conditions", nargs="+", choices=CONDITIONS, default=list(CONDITIONS))
    parser.add_argument("--embedder", choices=["sentence-transformer", "hashing"], default="sentence-transformer")
    parser.add_argument("--embedder-model", default="BAAI/bge-base-en-v1.5")
    args = parser.parse_args()

    engines = available_engines()
    requests = load_requests()
    qrels = load_rs_qrels(set(engines))
    origin = load_origin(set(engines))
    vertical = load_verticals()
    judged = [q for q in requests if q in qrels and q in origin and max(qrels[q].values()) > 0]
    print(f"{len(engines)} engines, {len(judged)} requests with origin + graded qrels", flush=True)
    embedder = (CachedEmbedder(SentenceTransformerEmbedder(args.embedder_model))
                if args.embedder == "sentence-transformer" else HashingEmbedder())
    vecs = {q: _normalise(v) for q, v in zip(judged, embedder.embed([requests[q] for q in judged]))}

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = time.strftime("%Y%m%d-%H%M%S")
    rows: list[dict] = []
    for seed in args.seeds:
        rng = random.Random(seed)
        node_docs = {e: sample_corpus(e, args.docs_per_engine, args.scan_lines, rng) for e in engines}
        profiles = build_node_profiles(node_docs, embedder, k=3, seed=seed)
        order = list(judged)
        random.Random(seed).shuffle(order)
        split = len(order) // 2
        train_ids, test_ids = order[:split], order[split:]
        print(f"seed {seed}: profiles ready; {len(train_ids)} train / {len(test_ids)} test requests", flush=True)

        for condition in args.conditions:
            cond_rng = random.Random(seed * 1000 + hash(condition) % 997)
            random_router = RandomRouter(seed=seed)
            random_router.register_sources(list(profiles.values()))
            observer = SourceInferenceObserver()
            records: dict[str, tuple[list[str], list[str]]] = {}
            hits, gains, contacts, off = [], [], [], []
            for q in order:
                grades = qrels[q]
                dispatched, decoys = dispatch(condition, vecs[q], profiles, grades, max_nodes=args.max_nodes,
                                              genuine_k=args.genuine_k, coarse_k=args.coarse_k,
                                              rng=cond_rng, random_router=random_router)
                records[q] = (dispatched, decoys)
                hits.append(1.0 if origin[q] in dispatched else 0.0)
                gains.append(captured_gain(dispatched, grades))
                contacts.append(len(dispatched))
                off.append(len([e for e in dispatched if e != origin[q]]))
                observer.observe(origin[q], dispatched)

            row = {"seed": seed, "condition": condition, "queries": len(order),
                   "origin_contacted": float(np.mean(hits)), "captured_gain": float(np.nanmean(gains)),
                   "contacts": float(np.mean(contacts)), "contacts_not_origin": float(np.mean(off))}

            # Topic attacks, two label granularities.
            for name, label_of in (("engine", origin), ("vertical", {q: vertical[origin[q]] for q in order})):
                labels = sorted(set(label_of[q] for q in order))
                history = [(records[q][0], label_of[q]) for q in train_ids]
                tests = [(records[q][0], label_of[q]) for q in test_ids]
                learned = evaluate(HistoryAttacker().fit(history), tests, labels)
                source_label = {e: (e if name == "engine" else vertical[e]) for e in engines}
                floor = evaluate(SetPriorAttacker(source_label, seed=seed), tests, labels)
                row.update({f"topic_{name}_acc": learned["accuracy"], f"topic_{name}_f1": learned["macro_f1"],
                            f"topic_{name}_top3": learned["top3_accuracy"],
                            f"topic_{name}_floor_acc": floor["accuracy"], f"topic_{name}_chance": learned["chance"]})

            # Source attack (topic -> origin engine) from contact counts.
            precisions = []
            for topic in set(origin[q] for q in order):
                guess = observer.infer_topic_sources(topic, 1)
                if guess:
                    precisions.append(1.0 if guess[0] == topic else 0.0)
            row["source_attack_acc"] = float(np.mean(precisions)) if precisions else float("nan")

            # Decoy stability within topic.
            by_topic: dict[str, list[set]] = defaultdict(list)
            for q in order:
                if records[q][1]:
                    by_topic[origin[q]].append(set(records[q][1]))
            pair_j = []
            for sets in by_topic.values():
                sample = sets[:40]
                pair_j.extend(jaccard(a, b) for i, a in enumerate(sample) for b in sample[i + 1:])
            row["decoy_jaccard"] = float(np.mean(pair_j)) if pair_j else float("nan")
            rows.append(row)
            print(f"  {condition:<14} origin {row['origin_contacted']:.3f} gain {row['captured_gain']:.3f} "
                  f"contacts {row['contacts']:.1f} | topic acc {row['topic_engine_acc']:.3f} "
                  f"(floor {row['topic_engine_floor_acc']:.3f}, chance {row['topic_engine_chance']:.3f}) "
                  f"F1 {row['topic_engine_f1']:.3f} | source {row['source_attack_acc']:.3f} "
                  f"| decoy J {row['decoy_jaccard']:.2f}", flush=True)
        _write(RESULTS_DIR / f"leakage_{run_id}_per_seed.csv", rows)

    metrics = [k for k in rows[0] if k not in ("seed", "condition", "queries")]
    summary = []
    for condition in args.conditions:
        group = [r for r in rows if r["condition"] == condition]
        entry = {"condition": condition, "seeds": len(group), "queries": group[0]["queries"]}
        for m in metrics:
            vals = [r[m] for r in group]
            entry[f"{m}_mean"] = float(np.nanmean(vals))
            entry[f"{m}_std"] = float(np.nanstd(vals))
        summary.append(entry)
    out = RESULTS_DIR / f"leakage_{run_id}.csv"
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
