"""Same-domain healthcare federation — the hard case (docs/40).

docs/36 and docs/39 route across 13 engines from six verticals, where a
biomedical query is easy to send to a biomedical engine. A realistic
federation of hospitals or institutes is same-domain: every source is
medical and differs by speciality. This builds that federation from the
public biomedical BEIR corpora available locally, with no patient data:

- pool nfcorpus (PubMed nutrition/medicine), scifact (biomedical claims)
  and trec-covid (COVID literature) documents;
- partition the pool into `--clients` SEMANTIC clients by spherical
  k-means on bge-base embeddings (a client = one region of medical topic
  space, the stand-in for a speciality), with uneven sizes as they fall;
- queries are the three corpora's judged queries; a query's relevant
  clients are the clients holding its qrel-relevant documents; its topic
  label is the client holding most of them.

Then the docs/39 conditions are run unchanged and the same table is
produced: routing quality, contacted-set → topic attack (learned observer
and metadata floor), source attack, decoy stability, contacts. Because
every client is biomedical there is no vertical to lean on: the observer
must learn speciality from the pattern alone, and decoy cells cannot be
made vertical-diverse — `build_cells` receives one group and falls back to
a fixed partition.

This is a simulated privacy-sensitive federation over public literature;
it says nothing about real institutional data. State that wherever it is
reported.

Run: python -m eval.run_healthcare
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import time
from collections import Counter, defaultdict

import numpy as np

from attacks.a2_source_inference import SourceInferenceObserver
from attacks.a2_topic_inference import HistoryAttacker, SetPriorAttacker, evaluate, jaccard
from baselines.base import SourceProfile
from baselines.random_router import RandomRouter
from eval.embed_cache import CachedEmbedder
from eval.run_leakage import dispatch
from eval.sweep import BEIR_DIR, RESULTS_DIR, HashingEmbedder, SentenceTransformerEmbedder, _normalise, load_qrels, select_queries
from nodes.profile import build_profile
from privacy.cluster_index import kmeans_unit
from router.anonymity import build_cells

CONDITIONS = ("random", "broadcast", "cosine@g", "cosine@K", "sticky_decoys", "random_decoys", "random_any",
              "cells_1x3", "cells_1x4", "cells_2x2", "oracle")


def load_pool(corpora: list[str], n_queries: int, scan_lines: int, seed: int, max_relevant: int = 20):
    """Documents (id -> text), queries (id -> text), qrels (query -> {doc}) over a bounded read.
    trec-covid judges ~1,000 documents per query; `max_relevant` keeps the
    highest-graded ones so one corpus does not swamp the pool."""
    rng = random.Random(seed)
    documents, queries, relevant = {}, {}, {}
    for corpus in corpora:
        corpus_dir = BEIR_DIR / corpus
        qrels = load_qrels(corpus_dir)
        chosen = select_queries(corpus_dir, qrels, n_queries, rng)
        for q in chosen:
            top = sorted(qrels[q], key=qrels[q].get, reverse=True)[:max_relevant]
            qrels[q] = {d: qrels[q][d] for d in top}
        required = {d for q in chosen for d in qrels[q]}
        seen = 0
        with (corpus_dir / "corpus.jsonl").open() as handle:
            for line in handle:
                if seen >= scan_lines and not required:
                    break
                obj = json.loads(line)
                did = f"{corpus}::{obj['_id']}"
                text = (obj.get("title", "").strip() + ". " + obj.get("text", "").strip()).strip(". ")
                if obj["_id"] in required:
                    documents[did] = text
                    required.discard(obj["_id"])
                elif seen < scan_lines and text:
                    documents[did] = text
                seen += 1
        for q, text in chosen.items():
            qid = f"{corpus}::{q}"
            queries[qid] = text
            relevant[qid] = {f"{corpus}::{d}" for d in qrels[q] if f"{corpus}::{d}" in documents}
    return documents, queries, {q: r for q, r in relevant.items() if r}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpora", nargs="+", default=["nfcorpus", "scifact", "trec-covid"])
    parser.add_argument("--clients", type=int, default=8)
    parser.add_argument("--n-queries-per-corpus", type=int, default=150)
    parser.add_argument("--scan-lines", type=int, default=4000, help="documents read per corpus beyond qrel-required")
    parser.add_argument("--max-nodes", type=int, default=4)
    parser.add_argument("--genuine-k", type=int, default=2)
    parser.add_argument("--coarse-k", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=[11, 22, 33])
    parser.add_argument("--conditions", nargs="+", choices=CONDITIONS, default=list(CONDITIONS))
    parser.add_argument("--embedder", choices=["sentence-transformer", "hashing"], default="sentence-transformer")
    parser.add_argument("--embedder-model", default="BAAI/bge-base-en-v1.5")
    args = parser.parse_args()

    embedder = (CachedEmbedder(SentenceTransformerEmbedder(args.embedder_model))
                if args.embedder == "sentence-transformer" else HashingEmbedder())
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = time.strftime("%Y%m%d-%H%M%S")
    rows: list[dict] = []
    for seed in args.seeds:
        started = time.perf_counter()
        documents, queries, relevant = load_pool(args.corpora, args.n_queries_per_corpus, args.scan_lines, seed)
        doc_ids = list(documents)
        doc_vecs = embedder.embed([documents[d] for d in doc_ids])
        doc_vecs = doc_vecs / np.maximum(np.linalg.norm(doc_vecs, axis=1, keepdims=True), 1e-12)
        centroids, assign = kmeans_unit(doc_vecs, args.clients, seed)
        client_of = {d: f"client_{int(a)}" for d, a in zip(doc_ids, assign.tolist())}
        sizes = Counter(client_of.values())
        profiles: dict[str, SourceProfile] = {}
        for c in sorted(sizes):
            members = doc_vecs[[i for i, d in enumerate(doc_ids) if client_of[d] == c]]
            profiles[c] = build_profile(c, members, k=3, sigma=0.0, rng=np.random.default_rng(seed), document_count=len(members))
        # Query labels: relevant clients (graded by count) and topic = the majority client.
        q_ids = [q for q in queries if relevant.get(q)]
        q_vecs = {q: _normalise(v) for q, v in zip(q_ids, embedder.embed([queries[q] for q in q_ids]))}
        grades = {q: dict(Counter(client_of[d] for d in relevant[q])) for q in q_ids}
        topic = {q: max(grades[q], key=grades[q].get) for q in q_ids}
        print(f"seed {seed}: {len(doc_ids)} docs -> {args.clients} clients {dict(sorted(sizes.items()))}; "
              f"{len(q_ids)} queries; prepared in {time.perf_counter() - started:.0f}s", flush=True)

        order = list(q_ids)
        random.Random(seed).shuffle(order)
        split = len(order) // 2
        train_ids, test_ids = order[:split], order[split:]
        group = {c: "biomedical" for c in profiles}  # one vertical: cells cannot be made diverse
        cells = {"cells_1x3": build_cells(list(profiles), group, 3), "cells_1x4": build_cells(list(profiles), group, 4),
                 "cells_2x2": build_cells(list(profiles), group, 2)}
        labels = sorted(profiles)

        for condition in args.conditions:
            cond_rng = random.Random(seed * 1000 + hash(condition) % 997)
            random_router = RandomRouter(seed=seed)
            random_router.register_sources(list(profiles.values()))
            observer = SourceInferenceObserver()
            records, hits, gains, contacts = {}, [], [], []
            for q in order:
                dispatched, decoys = dispatch(condition, q_vecs[q], profiles, grades[q], max_nodes=args.max_nodes,
                                              genuine_k=args.genuine_k, coarse_k=args.coarse_k, rng=cond_rng,
                                              random_router=random_router, cells=cells)
                records[q] = (dispatched, decoys)
                hits.append(1.0 if topic[q] in dispatched else 0.0)
                total = sum(grades[q].values())
                gains.append(sum(grades[q].get(c, 0) for c in dispatched) / total)
                contacts.append(len(dispatched))
                observer.observe(topic[q], dispatched)
            history = [(records[q][0], topic[q]) for q in train_ids]
            tests = [(records[q][0], topic[q]) for q in test_ids]
            learned = evaluate(HistoryAttacker().fit(history), tests, labels)
            floor = evaluate(SetPriorAttacker({c: c for c in profiles}, seed=seed), tests, labels)
            src = []
            for t in set(topic.values()):
                guess = observer.infer_topic_sources(t, 1)
                if guess:
                    src.append(1.0 if guess[0] == t else 0.0)
            by_topic = defaultdict(list)
            for q in order:
                if records[q][1]:
                    by_topic[topic[q]].append(set(records[q][1]))
            pair_j = [jaccard(a, b) for sets in by_topic.values() for i, a in enumerate(sets[:40]) for b in sets[:40][i + 1:]]
            row = {"seed": seed, "condition": condition, "queries": len(order), "clients": len(profiles),
                   "topic_client_contacted": float(np.mean(hits)), "relevant_doc_coverage": float(np.mean(gains)),
                   "contacts": float(np.mean(contacts)),
                   "topic_acc": learned["accuracy"], "topic_f1": learned["macro_f1"], "topic_top3": learned["top3_accuracy"],
                   "topic_floor_acc": floor["accuracy"], "topic_chance": learned["chance"],
                   "source_attack_acc": float(np.mean(src)) if src else float("nan"),
                   "decoy_jaccard": float(np.mean(pair_j)) if pair_j else float("nan")}
            rows.append(row)
            print(f"  {condition:<14} topic-client {row['topic_client_contacted']:.3f} coverage {row['relevant_doc_coverage']:.3f} "
                  f"contacts {row['contacts']:.1f} | topic acc {row['topic_acc']:.3f} (floor {row['topic_floor_acc']:.3f}, "
                  f"chance {row['topic_chance']:.3f}) | source {row['source_attack_acc']:.3f} | J {row['decoy_jaccard']:.2f}", flush=True)
        _write(RESULTS_DIR / f"healthcare_{run_id}_per_seed.csv", rows)

    metrics = [k for k in rows[0] if k not in ("seed", "condition", "queries", "clients")]
    summary = []
    for condition in args.conditions:
        group = [r for r in rows if r["condition"] == condition]
        entry = {"condition": condition, "seeds": len(group), "clients": group[0]["clients"]}
        for m in metrics:
            vals = [r[m] for r in group]
            entry[f"{m}_mean"] = float(np.nanmean(vals))
            entry[f"{m}_std"] = float(np.nanstd(vals))
        summary.append(entry)
    out = RESULTS_DIR / f"healthcare_{run_id}.csv"
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
