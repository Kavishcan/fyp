"""FeB4RAG resource-selection evaluation (docs/36).

The project's routing results so far (docs/31, 33) used virtual shards of
BEIR corpora with qrel-derived source labels. FeB4RAG (Wang et al., 2024) is
the labelled federated-search benchmark the proposal names as the main
routing dataset: 790 requests, 16 engines, and GRADED resource-selection
judgements (`BEIR-QRELS-RS.txt`, 0–75) for every request × engine pair. This
evaluates the same modes on it, with the ranking metrics the proposal lists.

Graded judgements matter here: most requests grade 10+ of 16 engines above
zero, so "did we contact any relevant engine" is trivially ~1.0 and says
nothing. Ranking quality is reported as nDCG@k, MRR and top-1 against the
graded qrels; the dispatched set is scored as the gain it captures relative
to the best possible set of the same size.

Engines: the 13 of 16 whose BEIR corpora are present locally (signal1m,
robust04 and trec-news are not BEIR). Qrels are restricted to those 13 and
nDCG ideals are computed over them, so numbers are for a 13-engine
federation, not FeB4RAG's 16.

Profiles: each engine's profile is built from a random sample of its corpus
(bounded scan of the first `--scan-lines` lines, then reservoir sample) with
the same bge-base model and k=3 centroids as docs/31. This is a clean split
— profiles never see the benchmark requests or their result pools.

Modes and cost/leakage metrics follow eval/run_mode_comparison.py; the
underlying profile ranking is shared by legacy and v2 (both rank locally), so
their ranking metrics coincide by construction and the modes differ in what
they dispatch.

Run: python -m eval.run_feb4rag
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from attacks.a2_source_inference import SourceInferenceObserver
from baselines.cosine_router import CosineRouter
from eval.embed_cache import CachedEmbedder
from eval.run_mode_comparison import dispatch_for_mode
from eval.sweep import (
    BEIR_DIR,
    REPO_ROOT,
    RESULTS_DIR,
    HashingEmbedder,
    SentenceTransformerEmbedder,
    _normalise,
    build_node_profiles,
)

FEB4RAG_DIR = REPO_ROOT / "backend" / "vendor" / "FeB4RAG" / "dataset"
ALL_ENGINES = ["nfcorpus", "fiqa", "arguana", "scidocs", "scifact", "trec-covid", "nq", "dbpedia-entity",
               "hotpotqa", "signal1m", "robust04", "trec-news", "msmarco", "fever", "climate-fever",
               "webis-touche2020"]


# --- data -------------------------------------------------------------------


def load_requests() -> dict[str, str]:
    out = {}
    with (FEB4RAG_DIR / "queries" / "requests.jsonl").open() as handle:
        for line in handle:
            obj = json.loads(line)
            out[obj["_id"]] = obj["text"]
    return out


def load_rs_qrels(engines: set[str]) -> dict[str, dict[str, float]]:
    """request id -> {engine: graded relevance}, restricted to `engines`."""
    qrels: dict[str, dict[str, float]] = defaultdict(dict)
    with (FEB4RAG_DIR / "qrels" / "BEIR-QRELS-RS.txt").open() as handle:
        for line in handle:
            qid, _, engine, score = line.split()
            if engine in engines:
                qrels[qid][engine] = float(score)
    return dict(qrels)


def available_engines() -> list[str]:
    return [e for e in ALL_ENGINES if (BEIR_DIR / e / "corpus.jsonl").exists()]


def sample_corpus(engine: str, n_docs: int, scan_lines: int, rng: random.Random) -> list[str]:
    """Reservoir-sample `n_docs` documents from the first `scan_lines` lines.
    Bounded so multi-GB corpora (msmarco: 8.8M lines) stay cheap; the sample
    is therefore drawn from a prefix of the file, not the whole corpus."""
    sample: list[str] = []
    seen = 0
    with (BEIR_DIR / engine / "corpus.jsonl").open() as handle:
        for line in handle:
            if seen >= scan_lines:
                break
            obj = json.loads(line)
            title = obj.get("title", "").strip()
            text = obj.get("text", "").strip()
            if not text:
                continue
            doc = f"{title}. {text}" if title else text
            seen += 1
            if len(sample) < n_docs:
                sample.append(doc)
            else:
                j = rng.randrange(seen)
                if j < n_docs:
                    sample[j] = doc
    return sample


# --- metrics ----------------------------------------------------------------


def dcg(gains: list[float]) -> float:
    return float(sum(g / np.log2(i + 2) for i, g in enumerate(gains)))


def ndcg_at(ranking: list[str], grades: dict[str, float], k: int) -> float:
    ideal = sorted(grades.values(), reverse=True)[:k]
    if not ideal or ideal[0] == 0:
        return float("nan")
    got = [grades.get(e, 0.0) for e in ranking[:k]]
    return dcg(got) / dcg(ideal)


def reciprocal_rank_of_best(ranking: list[str], grades: dict[str, float]) -> float:
    """1/rank of the first engine carrying the query's maximum grade."""
    best = max(grades.values()) if grades else 0.0
    if best == 0:
        return float("nan")
    for i, e in enumerate(ranking):
        if grades.get(e, 0.0) == best:
            return 1.0 / (i + 1)
    return 0.0


def top1_is_best(ranking: list[str], grades: dict[str, float]) -> float:
    best = max(grades.values()) if grades else 0.0
    if best == 0 or not ranking:
        return float("nan")
    return 1.0 if grades.get(ranking[0], 0.0) == best else 0.0


def captured_gain(dispatched: list[str], grades: dict[str, float]) -> float:
    """Gain of the contacted set relative to the best set of the same size."""
    if not dispatched:
        return 0.0
    ideal = sorted(grades.values(), reverse=True)[: len(dispatched)]
    if not ideal or sum(ideal) == 0:
        return float("nan")
    return sum(grades.get(e, 0.0) for e in dispatched) / sum(ideal)


# --- run --------------------------------------------------------------------


def rank_engines(query_vec: np.ndarray, profiles: dict) -> list[str]:
    router = CosineRouter(aggregation="max")
    router.register_sources(list(profiles.values()))
    return list(router.rank(query_vec, top_k=len(profiles)).ranked_source_ids)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--docs-per-engine", type=int, default=1500)
    parser.add_argument("--scan-lines", type=int, default=200_000)
    parser.add_argument("--max-nodes", type=int, default=6)
    parser.add_argument("--genuine-k", type=int, default=2)
    parser.add_argument("--coarse-k", type=int, default=12)
    parser.add_argument("--seeds", nargs="+", type=int, default=[11, 22, 33],
                        help="profile-sample seed; requests and qrels are fixed")
    parser.add_argument("--embedder", choices=["sentence-transformer", "hashing"], default="sentence-transformer")
    parser.add_argument("--embedder-model", default="BAAI/bge-base-en-v1.5")
    args = parser.parse_args()

    engines = available_engines()
    requests = load_requests()
    qrels = load_rs_qrels(set(engines))
    judged = [qid for qid in requests if qid in qrels and max(qrels[qid].values()) > 0]
    print(f"{len(engines)}/16 engines with local corpora: {engines}", flush=True)
    print(f"{len(judged)}/{len(requests)} requests with a positively graded engine among them", flush=True)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = time.strftime("%Y%m%d-%H%M%S")
    embedder = (
        CachedEmbedder(SentenceTransformerEmbedder(args.embedder_model))
        if args.embedder == "sentence-transformer" else HashingEmbedder()
    )
    raw_q = embedder.embed([requests[qid] for qid in judged])
    query_vectors = {qid: _normalise(v) for qid, v in zip(judged, raw_q)}

    per_seed: list[dict] = []
    for seed in args.seeds:
        started = time.perf_counter()
        rng = random.Random(seed)
        node_docs = {e: sample_corpus(e, args.docs_per_engine, args.scan_lines, rng) for e in engines}
        profiles = build_node_profiles(node_docs, embedder, k=3, seed=seed)
        print(f"seed {seed}: profiles from {sum(len(v) for v in node_docs.values())} sampled docs "
              f"in {time.perf_counter() - started:.0f}s", flush=True)

        # Ranking quality of the shared local profile ranking.
        rankings = {qid: rank_engines(query_vectors[qid], profiles) for qid in judged}
        rank_row = {"seed": seed, "mode": "profile_ranking", "queries": len(judged)}
        for k in (1, 3, 5):
            rank_row[f"ndcg@{k}"] = float(np.nanmean([ndcg_at(rankings[q], qrels[q], k) for q in judged]))
        rank_row["mrr_best"] = float(np.nanmean([reciprocal_rank_of_best(rankings[q], qrels[q]) for q in judged]))
        rank_row["top1_best"] = float(np.nanmean([top1_is_best(rankings[q], qrels[q]) for q in judged]))
        per_seed.append(rank_row)
        print(f"  ranking: nDCG@1 {rank_row['ndcg@1']:.3f} nDCG@3 {rank_row['ndcg@3']:.3f} "
              f"nDCG@5 {rank_row['ndcg@5']:.3f} MRR {rank_row['mrr_best']:.3f} top1 {rank_row['top1_best']:.3f}", flush=True)

        # Dispatch modes: what each mode actually contacts.
        np_rng = np.random.default_rng(seed)
        for mode in ("broadcast", "oracle", "smart", "v2", "legacy"):
            observer = SourceInferenceObserver()
            topic_truth, topic_counts = {}, {}
            gains, contacts, audit = [], [], []
            order = list(judged)
            random.Random(seed).shuffle(order)
            for qid in order:
                grades = qrels[qid]
                best = max(grades.values())
                relevant = {e for e, g in grades.items() if g == best}  # oracle/A2 truth: the best engine(s)
                topic_key = "|".join(sorted(relevant))
                dispatched = dispatch_for_mode(
                    mode, query_vectors[qid], profiles, topic_key, relevant,
                    max_nodes=args.max_nodes, genuine_k=args.genuine_k, coarse_k=args.coarse_k,
                    sigma=0.0, rng=np_rng,
                )
                gains.append(captured_gain(dispatched, grades))
                contacts.append(len(dispatched))
                audit.append(len([e for e in dispatched if grades.get(e, 0.0) == 0]))
                observer.observe(topic_key, dispatched)
                topic_truth[topic_key] = relevant
                topic_counts[topic_key] = topic_counts.get(topic_key, 0) + 1
            precisions = []
            for topic_key, truth in topic_truth.items():
                if topic_counts[topic_key] < 2:
                    continue
                guess = set(observer.infer_topic_sources(topic_key, len(truth)))
                if guess:
                    precisions.append(len(guess & truth) / len(guess))
            row = {"seed": seed, "mode": mode, "queries": len(judged),
                   "captured_gain": float(np.nanmean(gains)), "contacts": float(np.mean(contacts)),
                   "zero_grade_contacts": float(np.mean(audit)),
                   "a2_precision": float(np.mean(precisions)) if precisions else float("nan"),
                   "a2_topics": len(precisions)}
            per_seed.append(row)
            print(f"  {mode:<9} gain {row['captured_gain']:.3f} contacts {row['contacts']:.2f} "
                  f"zero-grade {row['zero_grade_contacts']:.2f} A2 {row['a2_precision']:.3f}", flush=True)

    fields = sorted({k for r in per_seed for k in r}, key=lambda k: (k not in ("mode", "seed", "queries"), k))
    with (RESULTS_DIR / f"feb4rag_{run_id}_per_seed.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(per_seed)
    summary = []
    for mode in dict.fromkeys(r["mode"] for r in per_seed):
        group = [r for r in per_seed if r["mode"] == mode]
        entry = {"mode": mode, "seeds": len(group), "engines": len(engines), "queries": group[0]["queries"]}
        for key in fields:
            if key in ("mode", "seed", "queries") or key not in group[0]:
                continue
            vals = [r[key] for r in group]
            entry[f"{key}_mean"] = float(np.nanmean(vals))
            entry[f"{key}_min"] = float(np.nanmin(vals))
            entry[f"{key}_max"] = float(np.nanmax(vals))
        summary.append(entry)
    sfields = sorted({k for r in summary for k in r}, key=lambda k: (k not in ("mode", "seeds", "engines", "queries"), k))
    out = RESULTS_DIR / f"feb4rag_{run_id}.csv"
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=sfields)
        writer.writeheader()
        writer.writerows(summary)
    print(json.dumps(summary, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
