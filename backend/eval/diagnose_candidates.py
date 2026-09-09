"""Post-hoc failure attribution. Gold labels never enter a runtime router."""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path

import numpy as np

from eval.run_candidate_study import CENTERED, REFERENCE, DATASETS, save_json
from eval.run_routing_study import ROOT, load_corpus
from eval.run_smart_pilot import fingerprint

STAGES = ("source_miss", "depth_miss", "rerank_miss", "recovered")


def attribute(relevant, contacted, candidates, final, assignment):
    """Exclusive per-gold-document buckets; their fractions sum to one."""
    if not relevant:
        raise ValueError("positive relevance judgments required")
    candidates, final, contacted = set(candidates), set(final), set(contacted)
    if not final.issubset(candidates):
        raise ValueError("final evidence must come from paid candidates")
    buckets = {s: [] for s in STAGES}
    for doc in sorted(relevant):
        source = f"source_{int(assignment[doc]):03d}"
        if doc in candidates and source not in contacted:
            raise ValueError("candidate belongs to an uncontacted source")
        stage = ("source_miss" if source not in contacted else "depth_miss" if doc not in candidates
                 else "rerank_miss" if doc not in final else "recovered")
        buckets[stage].append(int(doc))
    return buckets


def run(source, output):
    output.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((source / "manifest.json").read_text())
    for name, digest in {**manifest["inputs"], **manifest["artifacts"]}.items():
        if fingerprint(ROOT / name) != digest:
            raise ValueError(f"Study input changed: {name}")
    corpus, embeddings, assignments, ranks = {}, {}, {}, {}
    for dataset in DATASETS:
        docs, ids, texts, qrels = load_corpus(ROOT / "backend/vendor/beir" / dataset)
        corpus[dataset] = (docs, dict(zip(ids, texts)), qrels)
        path = (CENTERED if dataset == "scidocs" else REFERENCE) / f"{dataset}_embeddings.npz"
        with np.load(path) as z:
            embeddings[dataset] = (z["documents"], dict(zip(z["query_ids"].tolist(), z["queries"])))
        for seed in manifest["seeds"]:
            assignments[dataset, seed] = np.load(CENTERED / f"{dataset}_partition_{seed}.npy")
    groups, paired, examples = defaultdict(list), defaultdict(dict), []
    fields = ["dataset", "query_id", "seed", "method", "budget", "question", "relevant_count",
              *STAGES, "contacted", "quotas", "candidate_ids", "final_ids"]
    rows_written = 0
    with (output / "per-query.csv").open("w") as csv_stream, (output / "per-document.jsonl").open("w") as detail:
        writer = csv.DictWriter(csv_stream, fieldnames=fields)
        writer.writeheader()
        with (source / "decisions.jsonl").open() as stream:
            for line in stream:
                r = json.loads(line)
                if r["budget"] != 12 or r["method"] not in {"equal", "proportional", "joint"}:
                    continue
                dataset, seed, qid, method = r["dataset"], r["seed"], r["query_id"], r["method"]
                trace = r["trace"]
                candidates = {int(a["document_id"]) for a in trace["actions"] if "document_id" in a and not a["error"]}
                final = [int(i) for i in trace["final_document_ids"]]
                docs, questions, qrels = corpus[dataset]
                assignment = assignments[dataset, seed]
                buckets = attribute(qrels[qid], trace["contacted"], candidates, final, assignment)
                fractions = {s: len(buckets[s]) / len(qrels[qid]) for s in STAGES}
                if not np.isclose(fractions["recovered"], r["document_recall_at_5"]):
                    raise ValueError("Attribution disagrees with saved metric")
                key = dataset, seed, qid
                if key not in ranks:
                    vectors, queries = embeddings[dataset]
                    scores = vectors @ queries[qid]
                    ranks[key] = {}
                    for source_id in set(int(assignment[i]) for i in qrels[qid]):
                        pool = np.flatnonzero(assignment == source_id)
                        order = pool[np.argsort(-scores[pool], kind="stable")]
                        ranks[key].update({int(i): rank + 1 for rank, i in enumerate(order) if int(i) in qrels[qid]})
                gold = [dict(document_index=i, document_id=str(docs[i]["_id"]), title=docs[i].get("title", ""),
                             source_id=f"source_{int(assignment[i]):03d}", local_rank=ranks[key][i],
                             requested_quota=trace["quotas"].get(f"source_{int(assignment[i]):03d}", 0), stage=s)
                        for s, values in buckets.items() for i in values]
                compact = dict(dataset=dataset, seed=seed, query_id=qid, question=questions[qid], method=method,
                               budget=12, relevant_count=len(qrels[qid]), **fractions,
                               contacted=trace["contacted"], quotas=trace["quotas"],
                               candidate_ids=sorted(candidates), final_ids=final)
                writer.writerow({k: json.dumps(v) if isinstance(v, (list, dict)) else v for k, v in compact.items()})
                detail.write(json.dumps({**compact, "gold_documents": gold}) + "\n")
                groups[dataset, method].append(fractions)
                if method in {"joint", "equal"}:
                    paired[dataset, seed, qid][method] = {**compact, "gold_documents": gold}
                rows_written += 1
    summary = [dict(dataset=d, method=m, cases=len(rows), **{s: float(np.mean([r[s] for r in rows])) for s in STAGES})
               for (d, m), rows in sorted(groups.items())]
    comparisons = []
    for dataset in DATASETS:
        pairs = [p for (d, _, _), p in paired.items() if d == dataset]
        if any(set(p) != {"joint", "equal"} for p in pairs):
            raise ValueError("Unpaired diagnosis")
        for metric in ("recovered", "source_miss"):
            differences = [p["joint"][metric] - p["equal"][metric] for p in pairs]
            comparisons.append(dict(dataset=dataset, metric=metric, cases=len(pairs),
                                    higher=sum(x > 1e-12 for x in differences),
                                    lower=sum(x < -1e-12 for x in differences),
                                    tied=sum(abs(x) <= 1e-12 for x in differences)))
        # Explicitly selected extremes in BOTH directions, never presented as
        # representative averages. Full rows remain available for inspection.
        for direction in ("helped", "hurt"):
            sign = 1 if direction == "helped" else -1
            ordered = sorted(pairs, key=lambda p: (-sign * (p["joint"]["recovered"] - p["equal"]["recovered"]),
                                                  p["equal"]["query_id"], p["equal"]["seed"]))
            used = set()
            for pair in ordered:
                delta = pair["joint"]["recovered"] - pair["equal"]["recovered"]
                if sign * delta <= 0:
                    break
                if pair["equal"]["query_id"] in used:
                    continue
                used.add(pair["equal"]["query_id"])
                examples.append(dict(direction=direction, difference=delta, **pair))
                if len(used) == 2:
                    break
    save_json(output / "summary.json", dict(stages=summary, comparisons=comparisons, rows=rows_written))
    save_json(output / "examples.json", examples)
    lines = ["# Query-level failure diagnosis", "", "Post-hoc, B=12, final K=5. Percent of gold documents, macro-averaged over queries/seeds.",
             "Buckets are mutually exclusive accounting, not proof of causal mechanisms.", "",
             "| Dataset | Method | Uncontacted source | Not retrieved from contacted source | Dropped from final 5 | Recovered |",
             "|---|---|---:|---:|---:|---:|"]
    for row in summary:
        lines.append(f"| {row['dataset']} | {row['method']} | " + " | ".join(f"{100*row[s]:.3f}%" for s in STAGES) + " |")
    lines += ["", "## Illustrative extremes", "", "Two distinct helped and hurt queries per dataset where available; selected by largest final-recall change, not representative sampling."]
    for example in examples:
        a, b = example["equal"], example["joint"]
        lines += ["", f"### {a['dataset']} / {a['query_id']} / seed {a['seed']}: {example['direction']}",
                  "", a["question"], "", f"Equal: {a['contacted']}, quotas {a['quotas']}; final recall {100*a['recovered']:.1f}%.",
                  f"Joint: {b['contacted']}, quotas {b['quotas']}; final recall {100*b['recovered']:.1f}%.",
                  "", "| Gold document ID | Source | Local rank | Equal stage | Joint stage |", "|---|---|---:|---|---|"]
        other = {g["document_id"]: g for g in b["gold_documents"]}
        for g in a["gold_documents"][:12]:
            lines.append(f"| {g['document_id']} | {g['source_id']} | {g['local_rank']} | {g['stage']} | {other[g['document_id']]['stage']} |")
        if len(a["gold_documents"]) > 12:
            lines.append("Additional gold documents are in examples.json and per-document.jsonl.")
    (output / "report.md").write_text("\n".join(lines) + "\n")
    save_json(output / "manifest.json", dict(completed=True, source=str(source), rows=rows_written,
              source_decisions_sha256=fingerprint(source / "decisions.jsonl"),
              code_sha256=fingerprint(Path(__file__)), summary_sha256=fingerprint(output / "summary.json")))
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "experiments/routing-study-candidates-v1")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.source, args.output)
