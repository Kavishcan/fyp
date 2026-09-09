"""Exploratory matched-budget pilot using cached corpora/embeddings only."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import platform
import shutil
import subprocess
import time

import numpy as np

from baselines.base import SourceProfile
from eval.run_routing_study import ROOT, SEEDS, load_corpus, paired_interval
from eval.run_smart_pilot import fingerprint
from router.evidence_budget import AllocationConfig, Candidate, METHODS, allocate, prepare_profiles

REFERENCE = ROOT / "experiments/routing-study-v1"
CENTERED = ROOT / "experiments/routing-study-centered-test-v1"
DATASETS = ("scifact", "nfcorpus", "scidocs")
BUDGETS = (6, 12)


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def oracle_prefix_hits(rankings, relevant, max_sources, budget):
    """Exact offline upper bound for disjoint shards; never a routing policy.

    Multiple-choice knapsack: choose one prefix per source, constrained by
    both the number of positive prefixes and their total length.
    """
    dp = np.full((max_sources + 1, budget + 1), -np.inf)
    dp[0, 0] = 0
    for ranking in rankings.values():
        counts = np.cumsum([int(int(i) in relevant) for i in ranking[:budget]])
        nxt = dp.copy()
        for k, hits in enumerate(counts, 1):
            nxt[1:, k:] = np.maximum(nxt[1:, k:], dp[:-1, :-k] + hits)
        dp = nxt
    return int(np.max(dp))


def retrieval_metrics(result, relevant, assignment):
    retrieved = {int(p.document_id) for p in result.candidates}
    ranked = [int(p.document_id) for p in result.final]
    relevant_sources = {f"source_{int(assignment[i]):03d}" for i in relevant}
    dcg = sum((1 if i in relevant else 0) / np.log2(rank + 2) for rank, i in enumerate(ranked))
    ideal = sum(1 / np.log2(rank + 2) for rank in range(min(len(relevant), result.config.final_k)))
    return dict(candidate_recall=len(retrieved & relevant) / len(relevant),
                document_recall_at_5=len(set(ranked) & relevant) / len(relevant),
                ndcg_at_5=float(dcg / ideal) if ideal else 0.,
                source_recall=len(set(result.contacted) & relevant_sources) / len(relevant_sources),
                contacts=len(result.contacted), requests=len(result.actions), returned=len(result.candidates),
                text_bytes=result.to_dict()["text_bytes_received"], allocation_ms=result.elapsed_ms,
                budget_violation=int(len(result.contacted) > result.config.max_sources or
                                     len(result.actions) > result.config.candidate_budget or
                                     len(result.candidates) > result.config.candidate_budget))


def run(output, datasets=DATASETS):
    output.mkdir(parents=True, exist_ok=False)
    protocol = ROOT / "docs/20-evidence-budget-protocol.md"
    code = [Path(__file__), ROOT / "backend/router/evidence_budget.py",
            ROOT / "backend/eval/run_routing_study.py", ROOT / "backend/eval/run_smart_pilot.py", protocol]
    reference_meta = json.loads((REFERENCE / "metadata.json").read_text())
    centered_meta = json.loads((CENTERED / "evaluation.json").read_text())
    centered_manifest = json.loads((CENTERED / "run-manifest.json").read_text())
    manifest = dict(started_at=time.time(), completed=False, study="exploratory, previously inspected test sets",
                    datasets=list(datasets), source_count=30, seeds=SEEDS, candidate_budgets=BUDGETS,
                    contact_cap=3, final_k=5, methods=METHODS, parameters="fixed before this run; no tuning",
                    model=reference_meta["model"], snapshot=reference_meta["snapshot"],
                    max_sequence_length=reference_meta["max_sequence_length"],
                    python=platform.python_version(), numpy=np.__version__, platform=platform.platform(),
                    git_branch=subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
                    git_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                    git_status=subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True),
                    code={str(p.relative_to(ROOT)): fingerprint(p) for p in code}, inputs={}, artifacts={})
    for p in code:
        dst = output / "snapshot" / p.relative_to(ROOT)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dst)
    save_json(output / "manifest.json", manifest)
    records, oracle_rows = [], []
    with (output / "decisions.jsonl").open("w") as stream:
        for dataset in datasets:
            path = ROOT / "backend/vendor/beir" / dataset
            docs, ids, _, qrels = load_corpus(path)
            for name, expected in centered_meta["inputs"][dataset].items():
                actual = fingerprint(ROOT / name)
                if actual != expected:
                    raise ValueError(f"Cached corpus changed: {name}")
                manifest["inputs"][name] = actual
            base = CENTERED if dataset == "scidocs" else REFERENCE
            artifact = base / f"{dataset}_embeddings.npz"
            digest = fingerprint(artifact)
            expected = centered_manifest["reference"].get(str(artifact.relative_to(ROOT)))
            if expected and expected != digest:
                raise ValueError("Cached embedding artifact changed")
            manifest["artifacts"][str(artifact.relative_to(ROOT))] = digest
            with np.load(artifact) as archive:
                documents, queries = archive["documents"], archive["queries"]
                if list(archive["query_ids"]) != ids or list(archive["document_ids"]) != [str(d["_id"]) for d in docs]:
                    raise ValueError("Cached embedding IDs do not match corpus/query order")
            texts = [(d.get("title", "") + " " + d["text"]).strip() for d in docs]
            for seed in SEEDS:
                print(f"{dataset}, seed {seed}: {len(ids)} queries, five methods, B=6/12", flush=True)
                partition_path = CENTERED / f"{dataset}_partition_{seed}.npy"
                profiles_path = CENTERED / f"{dataset}_profiles_{seed}.npz"
                for p in (partition_path, profiles_path):
                    manifest["artifacts"][str(p.relative_to(ROOT))] = fingerprint(p)
                assignment = np.load(partition_path)
                if assignment.shape != (len(docs),) or not set(assignment).issubset(range(30)):
                    raise ValueError("Invalid partition")
                with np.load(profiles_path) as archive:
                    profiles = [SourceProfile(s, archive[s]) for s in sorted(archive.files)]
                shards = {p.source_id: np.flatnonzero(assignment == int(p.source_id.rsplit("_", 1)[1])) for p in profiles}
                for position, (qid, query) in enumerate(zip(ids, queries)):
                    # Simulator-side rank cache. Only the charged callback's
                    # single candidate enters allocate(), never these arrays.
                    scores = documents @ query
                    rankings = {s: pool[np.argsort(-scores[pool], kind="stable")[:max(BUDGETS)]]
                                for s, pool in shards.items()}

                    def retrieve(sid, offset):
                        ranking = rankings[sid]
                        if offset >= len(ranking):
                            return None
                        i = int(ranking[offset])
                        return Candidate(sid, str(i), texts[i], documents[i])

                    _, _, relevance, _, _ = prepare_profiles(query, profiles)
                    top_sources = sorted(relevance, key=lambda s: (-relevance[s], s))[:3]
                    for budget in BUDGETS:
                        oracle_rows.append(dict(dataset=dataset, query_id=qid, seed=seed, budget=budget,
                            fixed_source_oracle_recall=oracle_prefix_hits(
                                {s: rankings[s] for s in top_sources}, qrels[qid], 3, budget) / len(qrels[qid]),
                            joint_oracle_recall=oracle_prefix_hits(rankings, qrels[qid], 3, budget) / len(qrels[qid])))
                        methods = METHODS[position % len(METHODS):] + METHODS[:position % len(METHODS)]
                        for method in methods:
                            result = allocate(query, profiles, retrieve, AllocationConfig(3, budget, 5, method))
                            row = dict(dataset=dataset, scenario="clean", seed=seed, query_id=qid,
                                       budget=budget, method=method, **retrieval_metrics(result, qrels[qid], assignment))
                            records.append(row)
                            stream.write(json.dumps({**row, "trace": result.to_dict()}) + "\n")
                    if (position + 1) % 100 == 0:
                        print(f"  {position + 1}/{len(ids)}", flush=True)
                stream.flush()
                save_json(output / "manifest.json", manifest)
    metrics = ("candidate_recall", "document_recall_at_5", "ndcg_at_5", "source_recall", "contacts", "requests", "returned", "text_bytes", "allocation_ms")
    summary = []
    for dataset in datasets:
        for budget in BUDGETS:
            oracles = [r for r in oracle_rows if r["dataset"] == dataset and r["budget"] == budget]
            for method in METHODS:
                group = [r for r in records if (r["dataset"], r["budget"], r["method"]) == (dataset, budget, method)]
                summary.append(dict(dataset=dataset, budget=budget, method=method, cases=len(group),
                    **{m: float(np.mean([r[m] for r in group])) for m in metrics},
                    **{m: float(np.mean([r[m] for r in oracles])) for m in ("fixed_source_oracle_recall", "joint_oracle_recall")}))
    with (output / "summary.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    intervals = [paired_interval(records, dataset, budget, "joint", baseline, metric, bootstrap_seed=20260911)
                 for dataset in datasets for budget in BUDGETS for baseline in ("equal", "proportional", "profile_only", "allocation_only")
                 for metric in ("candidate_recall", "document_recall_at_5")]
    save_json(output / "intervals.json", intervals)
    save_json(output / "oracle.json", oracle_rows)
    manifest.update(completed=True, completed_at=time.time(), cases=len(records),
                    budget_violations=sum(r["budget_violation"] for r in records),
                    results_sha256=fingerprint(output / "summary.csv"))
    save_json(output / "manifest.json", manifest)
    print(f"Completed {len(records)} decisions; {manifest['budget_violations']} budget violations", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--datasets", nargs="+", choices=DATASETS, default=DATASETS)
    args = parser.parse_args()
    run(args.output, args.datasets)
