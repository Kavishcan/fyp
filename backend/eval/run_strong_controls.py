"""Tune stronger source-fusion controls on development, then audit frozen FiQA."""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path
import shutil
import time

import numpy as np

from baselines.base import SourceProfile
from baselines.profile_fusion import run_control
from eval.run_candidate_study import retrieval_metrics, save_json
from eval.run_feedback_study import load_data
from eval.run_rich_profile_study import CODE as ORIGINAL_CODE, KINDS
from eval.run_routing_study import ROOT, SEEDS, load_corpus, paired_interval
from eval.run_smart_pilot import fingerprint
from router.evidence_budget import Candidate
from router.lexical_profile import VERSION

WEIGHTS = (0., .25, .5, .75, 1.)
GRID = [("weighted_rrf", w, k) for w in WEIGHTS for k in (10, 60, 100)] + [
    ("minmax", w, 60) for w in WEIGHTS]
DEV = ROOT / "experiments/routing-study-rich-dev-v2"
TRANSFER = ROOT / "experiments/routing-study-rich-transfer-v1"
PROTOCOL = ROOT / "docs/28-strong-controls-protocol.md"
CODE = list(dict.fromkeys(ORIGINAL_CODE + [Path(__file__), ROOT / "backend/baselines/profile_fusion.py",
       ROOT / "backend/eval/prepare_answer_study.py", ROOT / "backend/eval/answer_quality.py", PROTOCOL]))


def choose_controls(rows):
    groups = sorted({(r["dataset"], r["kind"]) for r in rows})
    scores, selected = {}, {}
    if not groups:
        raise ValueError("empty development grid")
    for method, weight, constant in GRID:
        means = [[r["candidate_recall"] for r in rows if (r["dataset"], r["kind"]) == group
                  and (r["method"], r["weight"], r["constant"]) == (method, weight, constant)] for group in groups]
        if any(not values for values in means):
            raise ValueError("incomplete development grid")
        scores[method, weight, constant] = float(np.mean([np.mean(v) for v in means]))
    for method in ("weighted_rrf", "minmax"):
        key = min((key for key in scores if key[0] == method), key=lambda key: (-scores[key], key[1], key[2]))
        selected[method] = dict(weight=key[1], constant=key[2], development_recall=scores[key])
    return selected


def frozen_config(path):
    frozen = json.loads(path.read_text())
    if fingerprint(path.parent / "development.json") != frozen["development_sha256"]:
        raise ValueError("development results changed")
    for name, digest in frozen["code"].items():
        if fingerprint(ROOT / name) != digest:
            raise ValueError(f"frozen code changed: {name}")
    if set(frozen["selected"]) != {"weighted_rrf", "minmax"}:
        raise ValueError("missing frozen controls")
    for method, config in frozen["selected"].items():
        if (method, config["weight"], config["constant"]) not in GRID:
            raise ValueError("invalid frozen setting")
    return frozen


def transfer_tasks(frozen):
    return [("semantic16", 0., 60), ("semantic21", 0., 60), ("lexical", 1., 60),
            ("rrf", .5, 60), ("hybrid", .25, 60)] + [
        (method, c["weight"], c["constant"]) for method, c in frozen["selected"].items()]


def verified_manifest(folder):
    manifest = json.loads((folder / "manifest.json").read_text())
    if not manifest["completed"] or fingerprint(folder / "summary.csv") != manifest["results_sha256"]:
        raise ValueError("incomplete or changed reference run")
    for section in ("code", "inputs", "artifacts"):
        for name, digest in manifest[section].items():
            if fingerprint(ROOT / name) != digest:
                raise ValueError(f"changed reference {section}: {name}")
    return manifest


def cached_scenario(folder, n):
    assignment = np.load(folder / "assignment.npy")
    sketches = json.loads((folder / "sketches.json").read_text())
    profiles = []
    for size in (16, 21):
        with np.load(folder / f"profiles{size}.npz") as z:
            profiles.append([SourceProfile(s, z[s], lexical_sketch=sketches[s] if size == 16 else "",
                                           lexical_version=VERSION if size == 16 else "") for s in sorted(z.files)])
    if assignment.shape != (n,) or set(assignment) != set(range(30)):
        raise ValueError("invalid source assignment")
    pools = {p.source_id: np.flatnonzero(assignment == int(p.source_id.rsplit("_", 1)[1])) for p in profiles[0]}
    return assignment, pools, *profiles


def start_manifest(output, stage):
    output.mkdir(parents=True, exist_ok=False)
    manifest = dict(stage=stage, completed=False, started_at=time.time(), inputs={},
                    code={str(p.relative_to(ROOT)): fingerprint(p) for p in CODE},
                    contact_cap=3, candidate_budget=12, final_k=5,
                    study="stronger-baseline audit; FiQA previously inspected", numpy=np.__version__)
    for p in CODE:
        target = output / "snapshot" / p.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
    save_json(output / "manifest.json", manifest)
    return manifest


def write_summary(output, records):
    groups = defaultdict(list)
    for r in records:
        groups[r["dataset"], r["kind"], r["method"], r["weight"], r["constant"]].append(r)
    metrics = ("candidate_recall", "document_recall_at_5", "ndcg_at_5", "source_recall", "contacts", "requests", "returned")
    summary = [dict(dataset=d, kind=k, method=m, weight=w, constant=c, cases=len(rows),
                    **{metric: float(np.mean([r[metric] for r in rows])) for metric in metrics})
               for (d, k, m, w, c), rows in sorted(groups.items())]
    with (output / "summary.csv").open("w") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    return summary


def run(stage, output, frozen_path=None):
    output = output.resolve()
    frozen = frozen_config(frozen_path) if stage == "transfer" else None
    base = TRANSFER if frozen else DEV
    reference = verified_manifest(base)
    manifest = start_manifest(output, stage)
    manifest["reference_manifest_sha256"] = fingerprint(base / "manifest.json")
    manifest["reference_directory"] = str(base.relative_to(ROOT))
    manifest["model"] = reference["model"]
    manifest["snapshot"] = reference["snapshot"]
    if frozen:
        shutil.copy2(frozen_path, output / "frozen.json")
    tasks = transfer_tasks(frozen) if frozen else GRID
    records = []
    with (output / "decisions.jsonl").open("w") as stream:
        for dataset in (("fiqa",) if frozen else ("scifact", "nfcorpus")):
            path = ROOT / "backend/vendor/beir" / dataset
            if frozen:
                docs, ids, questions, qrels = load_corpus(path)
                with np.load(base / "fiqa_embeddings.npz") as z:
                    documents, queries = z["documents"], z["queries"]
                    if z["document_ids"].tolist() != [str(d["_id"]) for d in docs] or z["query_ids"].tolist() != ids:
                        raise ValueError("embedding ID mismatch")
            else:
                docs, ids, qrels, documents, queries = load_data(dataset, "develop", manifest)
                with (path / "queries.jsonl").open() as f:
                    by_id = {str(q["_id"]): q["text"] for q in map(json.loads, f)}
                questions = [by_id[q] for q in ids]
            texts = [(d.get("title", "") + " " + d["text"]).strip() for d in docs]
            for kind in KINDS:
                for seed in SEEDS:
                    print(f"{stage}: {dataset}/{kind}/{seed}, {len(ids)} queries, {len(tasks)} controls", flush=True)
                    assignment, pools, p16, p21 = cached_scenario(base / f"{dataset}-{kind}-{seed}", len(docs))
                    for qid, question, query in zip(ids, questions, queries):
                        scores = documents @ query
                        rankings = {s: pool[np.argsort(-scores[pool], kind="stable")[:12]] for s, pool in pools.items()}

                        def retrieve(sid, offset):
                            if offset >= len(rankings[sid]):
                                return None
                            i = int(rankings[sid][offset])
                            return Candidate(sid, str(i), texts[i], documents[i])

                        for method, weight, constant in tasks:
                            result = run_control(query, question, p21 if method == "semantic21" else p16,
                                                 retrieve, method, weight, constant)
                            row = dict(dataset=dataset, kind=kind, scenario="clean", budget=12, seed=seed, query_id=qid,
                                       method=method, weight=weight, constant=constant,
                                       **retrieval_metrics(result, qrels[qid], assignment))
                            records.append(row)
                            stream.write(json.dumps({**row, "trace": result.to_dict()}) + "\n")
                    stream.flush()
    summary = write_summary(output, records)
    if not frozen:
        selected = choose_controls(records)
        save_json(output / "development.json", dict(selected=selected, summary=summary))
        save_json(output / "frozen.json", dict(selected=selected, code=manifest["code"],
                  development_sha256=fingerprint(output / "development.json")))
        print(f"Frozen controls: {selected}", flush=True)
    else:
        with (base / "summary.csv").open() as f:
            prior = {(r["kind"], r["method"]): r for r in csv.DictReader(f)}
        for r in summary:
            if (r["kind"], r["method"]) in prior:
                for metric in ("candidate_recall", "document_recall_at_5", "ndcg_at_5", "source_recall"):
                    if not np.isclose(r[metric], float(prior[r["kind"], r["method"]][metric]), atol=1e-12, rtol=0):
                        raise ValueError("unchanged control failed reproduction check")
        intervals = [paired_interval([r for r in records if r["kind"] == kind], "fiqa", 12, "hybrid", baseline,
                                     metric, bootstrap_seed=20260914) | {"kind": kind}
                     for kind in KINDS for baseline in ("weighted_rrf", "minmax")
                     for metric in ("candidate_recall", "document_recall_at_5")]
        save_json(output / "intervals.json", intervals)
        manifest["unchanged_controls_reproduced"] = True
    manifest.update(completed=True, completed_at=time.time(), cases=len(records),
                    budget_violations=sum(r["budget_violation"] for r in records),
                    results_sha256=fingerprint(output / "summary.csv"))
    save_json(output / "manifest.json", manifest)
    print(f"Completed {len(records)} decisions; violations={manifest['budget_violations']}", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=("develop", "transfer"))
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--frozen", type=Path)
    a = p.parse_args()
    if a.stage == "transfer" and a.frozen is None:
        p.error("transfer requires --frozen")
    run(a.stage, a.output, a.frozen)
