"""Separate development selection and frozen exploratory transfer evaluation."""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path
import platform
import shutil
import time

import numpy as np

from baselines.base import SourceProfile
from eval.run_candidate_study import CENTERED, REFERENCE, DATASETS, retrieval_metrics, save_json
from eval.run_routing_study import ROOT, SEEDS, load_corpus, paired_interval
from eval.run_smart_pilot import fingerprint
from router.evidence_budget import AllocationConfig, Candidate, allocate

STRENGTHS = (0., .1, .25, .5)
DEV = ROOT / "experiments/routing-study-centered-dev-v1"
PROTOCOL = ROOT / "docs/24-feedback-routing-protocol.md"
CODE = [Path(__file__), ROOT / "backend/router/evidence_budget.py",
        ROOT / "backend/eval/run_candidate_study.py", ROOT / "backend/eval/run_routing_study.py",
        ROOT / "backend/eval/run_smart_pilot.py", PROTOCOL]


def normalized(text):
    return " ".join(text.casefold().split())


def choose_strength(rows):
    datasets = sorted({r["dataset"] for r in rows})
    if not datasets:
        raise ValueError("empty development results")
    scores = {}
    for alpha in STRENGTHS:
        groups = [[r["candidate_recall"] for r in rows if r["dataset"] == d and r["strength"] == alpha]
                  for d in datasets]
        if any(not g for g in groups):
            raise ValueError("missing development strength/dataset")
        scores[alpha] = float(np.mean([np.mean(g) for g in groups]))
    return min(scores, key=lambda a: (-scores[a], a)), scores


def record_input(path, manifest, expected=None):
    digest = fingerprint(path)
    if expected is not None and expected != digest:
        raise ValueError(f"Input changed: {path}")
    manifest["inputs"][str(path.relative_to(ROOT))] = digest


def load_data(dataset, stage, manifest):
    path = ROOT / "backend/vendor/beir" / dataset
    original = json.loads((ROOT / "experiments/routing-study-candidates-v1/manifest.json").read_text())
    for name, digest in original["inputs"].items():
        if name.startswith(str(path.relative_to(ROOT)) + "/"):
            record_input(ROOT / name, manifest, digest)
    split = ("train" if dataset == "scifact" else "dev") if stage == "develop" else "test"
    docs, ids, texts, qrels = load_corpus(path, split)
    embedding_path = (CENTERED if dataset == "scidocs" else REFERENCE) / f"{dataset}_embeddings.npz"
    record_input(embedding_path, manifest, original["artifacts"][str(embedding_path.relative_to(ROOT))])
    with np.load(embedding_path) as z:
        documents = z["documents"]
        if list(z["document_ids"]) != [str(d["_id"]) for d in docs]:
            raise ValueError("Document order mismatch")
        test_vectors, test_ids = z["queries"], z["query_ids"].tolist()
    if stage == "develop":
        previous = json.loads((DEV / "development-results.json").read_text())["splits"][dataset]
        record_input(path / f"qrels/{split}.tsv", manifest, previous["qrels_sha256"])
        _, _, test_texts, _ = load_corpus(path)
        forbidden = {normalized(t) for t in test_texts}
        ids = [qid for qid, text in zip(ids, texts) if normalized(text) not in forbidden]
        artifact = DEV / f"{dataset}_development.npz"
        record_input(artifact, manifest)
        with np.load(artifact) as z:
            queries = z["queries"]
            if z["query_ids"].tolist() != ids:
                raise ValueError("Development cache ID/split mismatch")
    else:
        if test_ids != ids:
            raise ValueError("Test query ID mismatch")
        queries = test_vectors
    return docs, ids, qrels, documents, queries


def validate_frozen(path):
    frozen = json.loads(path.read_text())
    if frozen["strength"] not in STRENGTHS:
        raise ValueError("Unregistered feedback strength")
    if fingerprint(path.parent / "development.json") != frozen["development_sha256"]:
        raise ValueError("Development results changed after selection")
    for name, digest in frozen["code"].items():
        if fingerprint(ROOT / name) != digest:
            raise ValueError(f"Frozen code/protocol changed: {name}")
    return frozen


def run(stage, output, frozen_path=None):
    frozen = validate_frozen(frozen_path) if stage == "evaluate" else None
    output.mkdir(parents=True, exist_ok=False)
    manifest = dict(stage=stage, completed=False, started_at=time.time(),
                    study="exploratory; historical tests previously inspected", inputs={},
                    python=platform.python_version(), numpy=np.__version__,
                    code={str(p.relative_to(ROOT)): fingerprint(p) for p in CODE},
                    seeds=SEEDS, contact_cap=3, candidate_budget=12, final_k=5,
                    strengths=STRENGTHS if not frozen else [frozen["strength"]])
    for path in CODE:
        target = output / "snapshot" / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    if frozen:
        shutil.copy2(frozen_path, output / "frozen.json")
    save_json(output / "manifest.json", manifest)
    records = []
    datasets = ("scifact", "nfcorpus") if stage == "develop" else DATASETS
    with (output / "decisions.jsonl").open("w") as stream:
        for dataset in datasets:
            docs, ids, qrels, documents, queries = load_data(dataset, stage, manifest)
            texts = [(d.get("title", "") + " " + d["text"]).strip() for d in docs]
            original = json.loads((ROOT / "experiments/routing-study-candidates-v1/manifest.json").read_text())
            for seed in SEEDS:
                pp, cp = CENTERED / f"{dataset}_partition_{seed}.npy", CENTERED / f"{dataset}_profiles_{seed}.npz"
                for p in (pp, cp):
                    record_input(p, manifest, original["artifacts"][str(p.relative_to(ROOT))])
                assignment = np.load(pp)
                with np.load(cp) as z:
                    profiles = [SourceProfile(s, z[s]) for s in sorted(z.files)]
                shards = {p.source_id: np.flatnonzero(assignment == int(p.source_id.rsplit("_", 1)[1])) for p in profiles}
                print(f"{stage}: {dataset}, seed {seed}, {len(ids)} queries", flush=True)
                for position, (qid, query) in enumerate(zip(ids, queries)):
                    scores = documents @ query
                    rankings = {s: pool[np.argsort(-scores[pool], kind="stable")[:12]] for s, pool in shards.items()}

                    def get(sid, offset):
                        if offset >= len(rankings[sid]):
                            return None
                        i = int(rankings[sid][offset])
                        return Candidate(sid, str(i), texts[i], documents[i])

                    methods = ([("feedback", a) for a in STRENGTHS] if not frozen else
                               [("equal", 0.), ("proportional", 0.), ("joint", 0.), ("feedback", frozen["strength"])])
                    methods = methods[position % len(methods):] + methods[:position % len(methods)]
                    for method, strength in methods:
                        result = allocate(query, profiles, get, AllocationConfig(3, 12, 5, method, strength))
                        row = dict(dataset=dataset, scenario="clean", budget=12, seed=seed, query_id=qid,
                                   method=method, strength=strength, **retrieval_metrics(result, qrels[qid], assignment))
                        records.append(row)
                        stream.write(json.dumps({**row, "trace": result.to_dict()}) + "\n")
                stream.flush()
                save_json(output / "manifest.json", manifest)
    groups = defaultdict(list)
    for r in records:
        groups[r["dataset"], r["method"], r["strength"]].append(r)
    metrics = ("candidate_recall", "document_recall_at_5", "ndcg_at_5", "source_recall", "contacts", "requests", "returned", "text_bytes", "allocation_ms")
    summary = [dict(dataset=d, method=m, strength=a, cases=len(rows),
                    **{k: float(np.mean([r[k] for r in rows])) for k in metrics})
               for (d, m, a), rows in sorted(groups.items())]
    with (output / "summary.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    if stage == "develop":
        strength, scores = choose_strength(records)
        save_json(output / "development.json", dict(summary=summary, macro_scores=scores))
        save_json(output / "frozen.json", dict(strength=strength, code=manifest["code"],
                  development_sha256=fingerprint(output / "development.json"),
                  selection="macro development candidate recall, exact ties prefer smaller alpha"))
        print(f"Frozen strength: {strength}; macro development recall: {scores}", flush=True)
    else:
        intervals = [paired_interval(records, d, 12, "feedback", b, metric, bootstrap_seed=20260912)
                     for d in datasets for b in ("equal", "proportional", "joint")
                     for metric in ("candidate_recall", "document_recall_at_5", "source_recall")]
        save_json(output / "intervals.json", intervals)
    manifest.update(completed=True, completed_at=time.time(), cases=len(records),
                    budget_violations=sum(r["budget_violation"] for r in records),
                    results_sha256=fingerprint(output / "summary.csv"))
    save_json(output / "manifest.json", manifest)
    print(f"Completed {len(records)} decisions; {manifest['budget_violations']} budget violations", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("develop", "evaluate"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frozen", type=Path)
    args = parser.parse_args()
    if args.stage == "evaluate" and args.frozen is None:
        parser.error("evaluate requires --frozen")
    run(args.stage, args.output, args.frozen)
