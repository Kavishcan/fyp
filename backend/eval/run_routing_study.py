"""Frozen-protocol clean routing and profile-cloning stress tests. Offline only."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import csv
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import time

import numpy as np

from baselines.base import SourceProfile
from eval.run_smart_pilot import fingerprint, partition_documents
from nodes.profile import build_profile
from router.smart import EvidenceTrust, SmartConfig, SmartRouter, SourceEvidence, _unit_rows

ROOT = Path(__file__).resolve().parents[2]
SEEDS = (11, 22, 33)
BUDGETS = (1, 3, 5)
MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def load_corpus(path):
    with (path / "corpus.jsonl").open() as stream:
        docs = [json.loads(line) for line in stream]
    with (path / "queries.jsonl").open() as stream:
        queries = {str(q["_id"]): q["text"] for q in map(json.loads, stream)}
    doc_index = {str(d["_id"]): i for i, d in enumerate(docs)}
    if len(doc_index) != len(docs):
        raise ValueError("Duplicate document IDs")
    qrels = {}
    with (path / "qrels/test.tsv").open() as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            if float(row["score"]) > 0:
                qrels.setdefault(row["query-id"], set()).add(doc_index[row["corpus-id"]])
    ids = sorted(qrels)
    return docs, ids, [queries[q] for q in ids], qrels


def score_profiles(query, profiles):
    return {p.source_id: float(np.clip(_unit_rows(np.asarray(p.centroids)) @ query, 0, 1).max())
            for p in profiles}


def fixed_rank(scores, budget):
    return sorted(scores, key=lambda sid: (-scores[sid], sid))[:budget]


def clean_metrics(selected, relevant, assignment, scores):
    selected_set = set(selected)
    relevant_sources = {f"source_{int(assignment[i]):03d}" for i in relevant}
    available = np.flatnonzero(np.isin(assignment, [int(s.rsplit("_", 1)[1]) for s in selected]))
    top = available[np.argsort(-scores[available], kind="stable")[:10]]
    return {
        "contacts": len(selected),
        "source_recall": len(selected_set & relevant_sources) / len(relevant_sources),
        "evidence_coverage": len(set(available) & relevant) / len(relevant),
        "document_recall_at_10": len(set(top) & relevant) / len(relevant),
        "empty_selection": int(not selected),
    }


def relative_config(budget):
    return SmartConfig(selection_policy="relative", aggregation="max", exposure_budget=budget,
                       max_sources=budget, relative_score_floor=.8, minimum_gain=0,
                       uncertainty_penalty=0)


def summarize(records):
    groups = {}
    for row in records:
        groups.setdefault((row["dataset"], row["scenario"], row["method"], row["budget"]), []).append(row)
    result = []
    for (dataset, scenario, method, budget), rows in sorted(groups.items()):
        item = dict(dataset=dataset, scenario=scenario, method=method, budget=budget, cases=len(rows),
                    unique_queries=len({r["query_id"] for r in rows}))
        for metric in ("contacts", "source_recall", "evidence_coverage", "document_recall_at_10",
                       "empty_selection", "malicious_contact"):
            item[metric] = float(np.mean([r[metric] for r in rows]))
        item["budget_violations"] = sum(r["budget_violation"] for r in rows)
        item["routing_p95_ms"] = float(np.percentile([r["routing_ms"] for r in rows], 95))
        for label, group in (("first50", [r for r in rows if r["position"] < 50]),
                             ("later", [r for r in rows if r["position"] >= 50])):
            item[f"{label}_malicious_contact"] = float(np.mean([r["malicious_contact"] for r in group])) if group else None
        result.append(item)
    return result


def paired_interval(records, dataset, budget, candidate, baseline, metric, resamples=10000):
    groups = {}
    for row in records:
        if (row["dataset"] == dataset and row["scenario"] == "clean" and row["budget"] == budget
                and row["method"] in (candidate, baseline)):
            groups.setdefault(row["query_id"], {}).setdefault(row["method"], {})[row["seed"]] = row[metric]
    differences = []
    for group in groups.values():
        if set(group) != {candidate, baseline} or set(group[candidate]) != set(group[baseline]):
            raise ValueError("Unpaired comparison")
        differences.append(np.mean([group[candidate][s] - group[baseline][s] for s in group[candidate]]))
    d = np.asarray(differences)
    if not len(d):
        raise ValueError("Empty comparison")
    bootstrap = np.random.default_rng(20260909).choice(d, (resamples, len(d)), replace=True).mean(axis=1)
    return dict(dataset=dataset, budget=budget, candidate=candidate, baseline=baseline, metric=metric,
                difference=float(d.mean()), ci95=np.quantile(bootstrap, [.025, .975]).tolist(),
                query_clusters=len(d))


def load_tasr():
    path = ROOT / "backend/vendor/routing-hijacking-fedrag/fedrag/rag/trust_defense.py"
    spec = importlib.util.spec_from_file_location("study_upstream_tasr", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.TrustAwareRouter


def attack_stream(queries, query_ids, qrels, documents, assignment, profiles, seed, scenario, method):
    profiles = list(profiles)
    attacker = "source_030"
    if scenario != "online_clean":
        profiles.append(SourceProfile(attacker, profiles[0].centroids.copy()))
    trust = EvidenceTrust()
    tasr = None
    if method.endswith("tasr"):
        tasr = load_tasr()(explore_interval=0)
        for p in profiles:
            tasr.register_client(p.source_id, np.asarray(p.centroids).mean(axis=0),
                                 np.empty((0, documents.shape[1])), p.centroids)
    router = SmartRouter()
    order = np.random.default_rng(seed + 2026).permutation(len(queries))
    indices = {f"source_{i:03d}": np.flatnonzero(assignment == i) for i in range(30)}
    for position, qi in enumerate(order):
        query = queries[qi]
        start = time.perf_counter()
        scores = score_profiles(query, profiles)
        evidence = {}
        for p in profiles:
            value, count = trust.get(p.source_id) if method == "relative_evidence" else (1., 0)
            if tasr:
                value = tasr.get_effective_score(p.source_id, top_k=3)
            evidence[p.source_id] = SourceEvidence(authorized=True, trust=value, observations=count)
        trace = None
        if method.startswith("fixed"):
            selected = fixed_rank({sid: value * evidence[sid].trust for sid, value in scores.items()}, 3)
        else:
            trace = router.route(query, profiles, evidence, relative_config(3))
            selected = trace.selected_source_ids
        elapsed = (time.perf_counter() - start) * 1000
        # The simulator owns all corpora; only selected-source results enter
        # the coordinator's feedback. No relevance labels enter routing/trust.
        doc_scores = documents @ query
        returned_ids, returned = [], {}
        for sid in selected:
            pool = indices["source_000"] if sid == attacker else indices[sid]
            top = pool[np.argsort(-doc_scores[pool], kind="stable")[:5]]
            if sid == attacker and scenario == "clone_empty":
                top = np.array([], dtype=int)
            returned_ids.extend(top.tolist())
            returned[sid] = documents[top]
            if method == "relative_evidence":
                p = next(p for p in profiles if p.source_id == sid)
                trust.observe(sid, p, returned[sid])
        if tasr:
            tasr.update_trust(query, selected, returned_docs=returned)
        relevant = qrels[query_ids[qi]]
        honest = [sid for sid in selected if sid != attacker]
        metric = clean_metrics(honest, relevant, assignment, doc_scores)
        pool = np.array(sorted(set(returned_ids)), dtype=int)
        top = pool[np.argsort(-doc_scores[pool], kind="stable")[:10]]
        metric.update(contacts=len(selected), empty_selection=int(not selected),
                      evidence_coverage=len(set(pool) & relevant) / len(relevant),
                      document_recall_at_10=len(set(top) & relevant) / len(relevant))
        yield dict(scenario=scenario, method=method, budget=3, seed=seed, query_id=query_ids[qi],
                   position=position, selected=selected, routing_ms=elapsed,
                   malicious_contact=int(attacker in selected), budget_violation=int(len(selected) > 3),
                   stop_reason=trace.stop_reason if trace else "fixed_top_k", **metric)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--datasets", nargs="+", choices=["scifact", "nfcorpus"], default=["scifact", "nfcorpus"])
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Choose a fresh output directory")
    args.output.mkdir(parents=True)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from huggingface_hub import snapshot_download
    from sentence_transformers import SentenceTransformer
    import torch
    torch.set_num_threads(4)
    snapshot = Path(snapshot_download(MODEL, local_files_only=True))
    model = SentenceTransformer(str(snapshot), local_files_only=True, device="cpu")
    metadata = dict(model=MODEL, snapshot=snapshot.name, max_sequence_length=model.max_seq_length,
                    seeds=SEEDS, budgets=BUDGETS, source_count=30, profile_sizes=[4, 16],
                    relative_configs={str(b): asdict(relative_config(b)) for b in BUDGETS},
                    platform=platform.platform(), inputs={}, profiles=[],
                    protocol_sha256=fingerprint(ROOT / "docs/16-routing-study-protocol.md"),
                    code_sha256={str(p.relative_to(ROOT)): fingerprint(p) for p in (
                        Path(__file__), ROOT / "backend/router/smart.py", ROOT / "backend/nodes/profile.py",
                        ROOT / "backend/vendor/routing-hijacking-fedrag/fedrag/rag/trust_defense.py")},
                    git_status=subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True))
    (args.output / "metadata.json").write_text(json.dumps(metadata, indent=2))
    records = []
    router = SmartRouter()
    with (args.output / "decisions.jsonl").open("w") as stream:
        for dataset in args.datasets:
            path = ROOT / "backend/vendor/beir" / dataset
            docs, ids, texts, qrels = load_corpus(path)
            metadata["inputs"][dataset] = {str(p.relative_to(ROOT)): fingerprint(p) for p in
                (path / "corpus.jsonl", path / "queries.jsonl", path / "qrels/test.tsv")}
            print(f"{dataset}: encoding {len(docs)} documents and {len(ids)} queries", flush=True)
            document_vectors = model.encode([(d.get("title", "") + " " + d["text"]).strip() for d in docs],
                                            batch_size=64, normalize_embeddings=True, show_progress_bar=False)
            query_vectors = model.encode(texts, batch_size=64, normalize_embeddings=True, show_progress_bar=False)
            np.savez_compressed(args.output / f"{dataset}_embeddings.npz", documents=document_vectors,
                                queries=query_vectors, query_ids=np.array(ids), document_ids=np.array([str(d["_id"]) for d in docs]))
            for seed in SEEDS:
                print(f"{dataset} seed {seed}: profiles and clean comparisons", flush=True)
                assignment = partition_documents(len(docs), 30, seed)
                np.save(args.output / f"{dataset}_partition_{seed}.npy", assignment)
                profile_sets = {}
                for k in (4, 16):
                    profile_sets[k] = [build_profile(f"source_{i:03d}", document_vectors[assignment == i],
                        k=k, sigma=0, rng=np.random.default_rng(seed + i), document_count=int(sum(assignment == i))) for i in range(30)]
                    artifact = args.output / f"{dataset}_profiles_{seed}_{k}.npz"
                    np.savez_compressed(artifact, **{p.source_id: p.centroids for p in profile_sets[k]})
                    metadata["profiles"].append(dict(dataset=dataset, seed=seed, centroids=k,
                        json_bytes=sum(len(json.dumps({"source_id":p.source_id,"centroids":p.centroids.tolist()}).encode()) for p in profile_sets[k]),
                        artifact_sha256=fingerprint(artifact)))
                for position, (qid, query) in enumerate(zip(ids, query_vectors)):
                    ds = document_vectors @ query
                    tasks = [("broadcast", None, 4)]
                    for b in BUDGETS:
                        tasks += [("fixed_coarse", b, 4), ("fixed_fine", b, 16),
                                  ("relative_coarse", b, 4), ("relative_fine", b, 16), ("old_overlap", b, 4)]
                    tasks = tasks[position % len(tasks):] + tasks[:position % len(tasks)]
                    for method, budget, k in tasks:
                        profiles = profile_sets[k]
                        start = time.perf_counter()
                        trace = None
                        if method == "broadcast":
                            selected = [p.source_id for p in profiles]
                        elif method.startswith("fixed"):
                            selected = fixed_rank(score_profiles(query, profiles), budget)
                        else:
                            cfg = (SmartConfig(exposure_budget=budget, max_sources=5) if method == "old_overlap"
                                   else relative_config(budget))
                            evidence = {p.source_id: SourceEvidence(authorized=True) for p in profiles}
                            trace = router.route(query, profiles, evidence, cfg)
                            selected = trace.selected_source_ids
                        row = dict(dataset=dataset, scenario="clean", method=method, budget=budget or 30,
                                   query_id=qid, seed=seed, position=position, selected=selected,
                                   routing_ms=(time.perf_counter()-start)*1000, malicious_contact=0,
                                   budget_violation=int(budget is not None and len(selected)>budget),
                                   stop_reason=trace.stop_reason if trace else "fixed_top_k",
                                   **clean_metrics(selected, qrels[qid], assignment, ds))
                        records.append(row)
                        stream.write(json.dumps(row) + "\n")
                for scenario in ("online_clean", "clone_empty", "clone_bait"):
                    print(f"{dataset} seed {seed}: {scenario}", flush=True)
                    for method in ("fixed", "relative", "relative_evidence", "fixed_tasr", "relative_tasr"):
                        for row in attack_stream(query_vectors, ids, qrels, document_vectors, assignment,
                                                 profile_sets[16], seed, scenario, method):
                            row["dataset"] = dataset
                            records.append(row)
                            stream.write(json.dumps(row) + "\n")
                stream.flush()
    result = summarize(records)
    with (args.output / "summary.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(result[0]))
        writer.writeheader()
        writer.writerows(result)
    intervals = [paired_interval(records, dataset, budget, candidate, baseline, metric)
                 for dataset in args.datasets for budget in BUDGETS
                 for candidate, baseline in (("fixed_fine", "fixed_coarse"), ("relative_fine", "fixed_fine"))
                 for metric in ("source_recall", "evidence_coverage", "document_recall_at_10", "contacts")]
    (args.output / "intervals.json").write_text(json.dumps(intervals, indent=2))
    metadata.update(cases=len(records), budget_violations=sum(r["budget_violation"] for r in records),
                    completed=True, result_sha256=fingerprint(args.output / "summary.csv"))
    (args.output / "metadata.json").write_text(json.dumps(metadata, indent=2))
    print(f"Completed: {len(records)} cases, {metadata['budget_violations']} budget violations", flush=True)


if __name__ == "__main__":
    main()
