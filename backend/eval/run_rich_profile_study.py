"""Rich-profile development, then fixed-parameter finance transfer evaluation."""
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
from sklearn.cluster import MiniBatchKMeans

from baselines.base import SourceProfile
from eval.run_candidate_study import retrieval_metrics, save_json
from eval.run_feedback_study import load_data
from eval.run_routing_study import ROOT, SEEDS, load_corpus, paired_interval
from eval.run_smart_pilot import fingerprint, partition_documents
from router.evidence_budget import AllocationConfig, allocate, Candidate, unit_rows
from router.lexical_profile import build_sketch, decode_sketch, lexical_scores, VERSION, BYTES

ALPHAS = (0., .25, .5, .75, 1.)
KINDS = ("random", "topic")
PROTOCOL = ROOT / "docs/26-rich-profile-protocol.md"
CODE = [Path(__file__), ROOT / "backend/router/lexical_profile.py", ROOT / "backend/router/evidence_budget.py",
        ROOT / "backend/nodes/metadata.py", ROOT / "backend/baselines/base.py",
        ROOT / "backend/eval/run_feedback_study.py", ROOT / "backend/eval/run_candidate_study.py",
        ROOT / "backend/eval/run_routing_study.py", ROOT / "backend/eval/run_smart_pilot.py",
        ROOT / "backend/eval/run_centered_study.py", PROTOCOL]


def cluster(vectors, k, seed):
    k = min(k, len(vectors))
    model = MiniBatchKMeans(n_clusters=k, random_state=seed, n_init=3,
                           max_iter=100, batch_size=512, reassignment_ratio=0.)
    labels = model.fit_predict(vectors)
    return labels, model.cluster_centers_


def scenario(vectors, texts, kind, seed, output):
    assignment = (partition_documents(len(texts), 30, seed) if kind == "random"
                  else cluster(vectors, 30, seed)[0])
    if len(set(assignment)) != 30:
        raise ValueError("Partition did not produce 30 nonempty sources")
    pools, profiles16, profiles21, stats = {}, [], [], []
    for i in range(30):
        sid = f"source_{i:03d}"
        indices = np.flatnonzero(assignment == i)
        pools[sid] = indices
        local_text = [texts[j] for j in indices]
        sketch = build_sketch(local_text)
        c16 = cluster(vectors[indices], 16, seed + i)[1].astype(np.float32)
        c21 = cluster(vectors[indices], 21, seed + i)[1].astype(np.float32)
        profiles16.append(SourceProfile(sid, c16, lexical_sketch=sketch, lexical_version=VERSION))
        profiles21.append(SourceProfile(sid, c21))
        stats.append(dict(source_id=sid, documents=len(indices), semantic16_bytes=c16.nbytes,
                          semantic21_bytes=c21.nbytes, hybrid_bytes=c16.nbytes + BYTES,
                          hybrid_json_bytes=len(json.dumps(dict(source_id=sid, centroids=c16.tolist(),
                              lexical_sketch=sketch, lexical_version=VERSION)).encode()),
                          semantic21_json_bytes=len(json.dumps(dict(source_id=sid, centroids=c21.tolist())).encode()),
                          sketch_occupancy=float(decode_sketch(sketch).mean())))
    np.save(output / "assignment.npy", assignment)
    np.savez_compressed(output / "profiles16.npz", **{p.source_id: p.centroids for p in profiles16})
    np.savez_compressed(output / "profiles21.npz", **{p.source_id: p.centroids for p in profiles21})
    save_json(output / "sketches.json", {p.source_id: p.lexical_sketch for p in profiles16})
    save_json(output / "profiles.json", stats)
    return assignment, pools, profiles16, profiles21, stats


def select_alpha(rows):
    groups = sorted({(r["dataset"], r["kind"]) for r in rows})
    scores = {}
    for alpha in ALPHAS:
        means = [[r["candidate_recall"] for r in rows if (r["dataset"], r["kind"]) == group
                  and r["method"] == "hybrid" and r["alpha"] == alpha] for group in groups]
        if not means or any(not values for values in means):
            raise ValueError("Incomplete alpha selection grid")
        scores[alpha] = float(np.mean([np.mean(values) for values in means]))
    return min(scores, key=lambda a: (-scores[a], a)), scores


def verify_frozen(path):
    frozen = json.loads(path.read_text())
    if frozen["alpha"] not in ALPHAS:
        raise ValueError("Invalid alpha")
    if fingerprint(path.parent / "development.json") != frozen["development_sha256"]:
        raise ValueError("Development results changed")
    for name, digest in frozen["code"].items():
        if fingerprint(ROOT / name) != digest:
            raise ValueError(f"Code/protocol changed: {name}")
    return frozen


def load_transfer(output, manifest):
    path = ROOT / "backend/vendor/beir/fiqa"
    for p in (path / "corpus.jsonl", path / "queries.jsonl", path / "qrels/test.tsv"):
        manifest["inputs"][str(p.relative_to(ROOT))] = fingerprint(p)
    docs, ids, texts, qrels = load_corpus(path)
    from eval.run_centered_study import encoder
    model = encoder()  # cached-only, verified against prior MiniLM snapshot
    print(f"FiQA: encoding {len(docs)} local documents / {len(ids)} test questions; no downloads", flush=True)
    documents = model.encode([(d.get("title", "") + " " + d["text"]).strip() for d in docs],
                             batch_size=64, normalize_embeddings=True, show_progress_bar=False)
    queries = model.encode(texts, batch_size=64, normalize_embeddings=True, show_progress_bar=False)
    artifact = output / "fiqa_embeddings.npz"
    np.savez_compressed(artifact, documents=documents, queries=queries,
                        document_ids=np.array([str(d["_id"]) for d in docs]), query_ids=np.array(ids))
    manifest["artifacts"][str(artifact.relative_to(ROOT))] = fingerprint(artifact)
    return docs, ids, texts, qrels, documents, queries


def run(stage, output, frozen_path=None):
    output = output.resolve()
    frozen = verify_frozen(frozen_path) if stage == "transfer" else None
    output.mkdir(parents=True, exist_ok=False)
    reference = json.loads((ROOT / "experiments/routing-study-v1/metadata.json").read_text())
    manifest = dict(stage=stage, completed=False, started_at=time.time(), inputs={}, artifacts={},
                    code={str(p.relative_to(ROOT)): fingerprint(p) for p in CODE},
                    model=reference["model"], snapshot=reference["snapshot"], max_sequence_length=256,
                    python=platform.python_version(), numpy=np.__version__, seeds=SEEDS, kinds=KINDS,
                    contact_cap=3, candidate_budget=12, final_k=5)
    for path in CODE:
        target = output / "snapshot" / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    if frozen:
        shutil.copy2(frozen_path, output / "frozen.json")
    save_json(output / "manifest.json", manifest)
    records, profile_stats = [], []
    with (output / "decisions.jsonl").open("w") as stream:
        for dataset in (("fiqa",) if frozen else ("scifact", "nfcorpus")):
            if frozen:
                docs, ids, questions, qrels, documents, queries = load_transfer(output, manifest)
            else:
                docs, ids, qrels, documents, queries = load_data(dataset, "develop", manifest)
                with (ROOT / "backend/vendor/beir" / dataset / "queries.jsonl").open() as source:
                    text_by_id = {str(q["_id"]): q["text"] for q in map(json.loads, source)}
                questions = [text_by_id[qid] for qid in ids]
            texts = [(d.get("title", "") + " " + d["text"]).strip() for d in docs]
            for kind in KINDS:
                for seed in SEEDS:
                    print(f"{stage}: {dataset}/{kind}, seed {seed}, profile construction", flush=True)
                    folder = output / f"{dataset}-{kind}-{seed}"
                    folder.mkdir()
                    assignment, pools, p16, p21, stats = scenario(documents, texts, kind, seed, folder)
                    profile_stats += [dict(dataset=dataset, kind=kind, seed=seed, **s) for s in stats]
                    for p in folder.iterdir():
                        manifest["artifacts"][str(p.relative_to(ROOT))] = fingerprint(p)
                    print(f"  {len(ids)} questions", flush=True)
                    for position, (qid, question, query) in enumerate(zip(ids, questions, queries)):
                        scores = documents @ query
                        rankings = {s: pool[np.argsort(-scores[pool], kind="stable")[:12]] for s, pool in pools.items()}

                        def get(sid, offset):
                            if offset >= len(rankings[sid]):
                                return None
                            i = int(rankings[sid][offset])
                            return Candidate(sid, str(i), texts[i], documents[i])

                        tasks = [("semantic16", "semantic", 0., p16), ("semantic21", "semantic", 0., p21),
                                 ("lexical", "lexical", 1., p16), ("rrf", "rrf", .5, p16)]
                        tasks += [("hybrid", "hybrid", a, p16) for a in ([frozen["alpha"]] if frozen else ALPHAS)]
                        tasks = tasks[position % len(tasks):] + tasks[:position % len(tasks)]
                        available = lexical_scores(question, p16) is not None
                        for method, strategy, alpha, profiles in tasks:
                            result = allocate(query, profiles, get,
                                              AllocationConfig(3, 12, 5, "equal", profile_strategy=strategy, lexical_weight=alpha),
                                              question=question)
                            row = dict(dataset=dataset, kind=kind, scenario="clean", budget=12, query_id=qid, seed=seed,
                                       method=method, alpha=alpha, lexical_available=int(available),
                                       **retrieval_metrics(result, qrels[qid], assignment))
                            records.append(row)
                            stream.write(json.dumps({**row, "trace": result.to_dict()}) + "\n")
                    stream.flush()
                    save_json(output / "manifest.json", manifest)
    metrics = ("candidate_recall", "document_recall_at_5", "ndcg_at_5", "source_recall", "contacts", "requests",
               "returned", "text_bytes", "allocation_ms", "lexical_available")
    groups = defaultdict(list)
    for r in records:
        groups[r["dataset"], r["kind"], r["method"], r["alpha"]].append(r)
    summary = [dict(dataset=d, kind=k, method=m, alpha=a, cases=len(rows),
                    **{metric: float(np.mean([r[metric] for r in rows])) for metric in metrics})
               for (d, k, m, a), rows in sorted(groups.items())]
    with (output / "summary.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    save_json(output / "profile-costs.json", profile_stats)
    if not frozen:
        alpha, scores = select_alpha(records)
        save_json(output / "development.json", dict(summary=summary, macro_scores=scores))
        save_json(output / "frozen.json", dict(alpha=alpha, code=manifest["code"],
                  development_sha256=fingerprint(output / "development.json")))
        print(f"Selected alpha: {alpha}; development macro candidate recall: {scores}", flush=True)
    else:
        intervals = [paired_interval([r for r in records if r["kind"] == kind], "fiqa", 12, "hybrid", baseline,
                                     metric, bootstrap_seed=20260913)
                     | {"kind": kind} for kind in KINDS
                     for baseline in ("semantic16", "semantic21", "lexical", "rrf")
                     for metric in ("candidate_recall", "document_recall_at_5")]
        save_json(output / "intervals.json", intervals)
    manifest.update(completed=True, completed_at=time.time(), cases=len(records),
                    budget_violations=sum(r["budget_violation"] for r in records),
                    results_sha256=fingerprint(output / "summary.csv"))
    save_json(output / "manifest.json", manifest)
    print(f"Completed {len(records)} decisions; {manifest['budget_violations']} budget violations", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("develop", "transfer"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frozen", type=Path)
    args = parser.parse_args()
    if args.stage == "transfer" and args.frozen is None:
        parser.error("transfer requires --frozen")
    run(args.stage, args.output, args.frozen)
