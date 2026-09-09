"""Development selection followed by a separately invoked frozen transfer run."""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
import json
import os
from pathlib import Path
import shutil
import time

import numpy as np

from baselines.base import SourceProfile
from eval.run_routing_study import (
    ROOT, MODEL, SEEDS, BUDGETS, attack_stream, clean_metrics, fixed_rank,
    load_corpus, paired_interval, relative_config, score_profiles, summarize,
)
from eval.run_smart_pilot import fingerprint, partition_documents
from nodes.profile import build_profile
from router.centering import center_profiles, center_query
from router.smart import SmartConfig, SmartRouter, SourceEvidence

REFERENCE = ROOT / "experiments/routing-study-v1"
STRENGTHS = (0., .25, .5, .75, 1.)


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def encoder():
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from huggingface_hub import snapshot_download
    from sentence_transformers import SentenceTransformer
    import torch
    torch.set_num_threads(4)
    snapshot = Path(snapshot_download(MODEL, local_files_only=True))
    reference = json.loads((REFERENCE / "metadata.json").read_text())
    if snapshot.name != reference["snapshot"]:
        raise ValueError("Encoder snapshot differs from frozen reference")
    model = SentenceTransformer(str(snapshot), local_files_only=True, device="cpu")
    if model.max_seq_length != reference["max_sequence_length"]:
        raise ValueError("Encoder sequence length differs from reference")
    return model


def verify_reference(dataset):
    metadata = json.loads((REFERENCE / "metadata.json").read_text())
    for path, digest in metadata["inputs"][dataset].items():
        if fingerprint(ROOT / path) != digest:
            raise ValueError(f"Reference input changed: {path}")


def frozen_profiles(dataset, seed):
    with np.load(REFERENCE / f"{dataset}_profiles_{seed}_16.npz") as archive:
        return [SourceProfile(sid, archive[sid]) for sid in sorted(archive.files)]


def centered_scores(query, prepared):
    offset, matrices = prepared
    q = center_query(query, offset)
    return {sid: float(np.clip(values @ q, 0, 1).max()) for sid, values in matrices.items()}


def budget_config(budget, strength, centered=True):
    return SmartConfig(aggregation="max", relevance_mode="centered" if centered else "centroid",
                       centering_strength=strength, selection_policy="relative", relative_score_floor=0,
                       minimum_gain=0, uncertainty_penalty=0, max_sources=budget, exposure_budget=budget)


def normalized_text(text):
    return " ".join(text.casefold().split())


def select_strength(rows):
    dataset_names = sorted({r["dataset"] for r in rows})
    scores = {a: float(np.mean([np.mean([r["source_recall"] for r in rows
              if r["dataset"] == name and r["strength"] == a]) for name in dataset_names])) for a in STRENGTHS}
    return min(scores, key=lambda a: (-scores[a], a)), scores


def development(output, model):
    rows, split_counts = [], {}
    for dataset, split in (("scifact", "train"), ("nfcorpus", "dev")):
        verify_reference(dataset)
        path = ROOT / "backend/vendor/beir" / dataset
        docs, ids, texts, qrels = load_corpus(path, split)
        _, _, test_texts, _ = load_corpus(path)
        test_set = {normalized_text(t) for t in test_texts}
        retained = [(qid, text) for qid, text in zip(ids, texts) if normalized_text(text) not in test_set]
        split_counts[dataset] = dict(split=split, original=len(ids), retained=len(retained),
                                    excluded=len(ids) - len(retained), qrels_sha256=fingerprint(path / f"qrels/{split}.tsv"))
        ids, texts = zip(*retained)
        vectors = model.encode(list(texts), normalize_embeddings=True, show_progress_bar=False)
        np.savez_compressed(output / f"{dataset}_development.npz", queries=vectors, query_ids=np.array(ids))
        print(f"Development {dataset}: {len(ids)} queries", flush=True)
        for seed in SEEDS:
            assignment = np.load(REFERENCE / f"{dataset}_partition_{seed}.npy")
            profiles = frozen_profiles(dataset, seed)
            for strength in STRENGTHS:
                prepared = center_profiles({p.source_id: p.centroids for p in profiles}, strength)
                recalls = []
                for qid, query in zip(ids, vectors):
                    relevant_sources = {f"source_{int(assignment[i]):03d}" for i in qrels[qid]}
                    selected = fixed_rank(centered_scores(query, prepared), 3)
                    recalls.append(len(set(selected) & relevant_sources) / len(relevant_sources))
                rows.append(dict(dataset=dataset, seed=seed, strength=strength, source_recall=float(np.mean(recalls))))
    strength, scores = select_strength(rows)
    save_json(output / "development-results.json", dict(rows=rows, macro_scores=scores, splits=split_counts))
    save_json(output / "frozen-config.json", dict(strength=strength, scores=scores,
              selection="macro development source recall at budget 3; ties prefer smaller strength",
              development_sha256=fingerprint(output / "development-results.json"),
              protocol_sha256=fingerprint(ROOT / "docs/18-centered-routing-protocol.md"),
              config=asdict(budget_config(3, strength))))
    print(f"Frozen strength: {strength}; development scores: {scores}", flush=True)


def evaluate(output, model, frozen_path):
    frozen = json.loads(frozen_path.read_text())
    if frozen["protocol_sha256"] != fingerprint(ROOT / "docs/18-centered-routing-protocol.md"):
        raise ValueError("Protocol changed after freezing")
    if frozen["development_sha256"] != fingerprint(frozen_path.parent / "development-results.json"):
        raise ValueError("Development results changed after freezing")
    strength = frozen["strength"]
    if strength not in STRENGTHS:
        raise ValueError("Unregistered strength")
    shutil.copy2(frozen_path, output / "frozen-config.json")
    records, inputs = [], {}
    router = SmartRouter()
    with (output / "decisions.jsonl").open("w") as stream:
        for dataset in ("scifact", "nfcorpus", "scidocs"):
            path = ROOT / "backend/vendor/beir" / dataset
            docs, ids, texts, qrels = load_corpus(path)
            inputs[dataset] = {str(p.relative_to(ROOT)): fingerprint(p) for p in
                              (path / "corpus.jsonl", path / "queries.jsonl", path / "qrels/test.tsv")}
            if dataset != "scidocs":
                verify_reference(dataset)
                with np.load(REFERENCE / f"{dataset}_embeddings.npz") as archive:
                    documents, queries = archive["documents"], archive["queries"]
                    assert list(archive["query_ids"]) == ids
                    assert list(archive["document_ids"]) == [str(d["_id"]) for d in docs]
            else:
                print(f"SCIDOCS: encoding {len(docs)} documents / {len(ids)} queries locally", flush=True)
                documents = model.encode([(d.get("title", "") + " " + d["text"]).strip() for d in docs],
                                         batch_size=64, normalize_embeddings=True, show_progress_bar=False)
                queries = model.encode(texts, batch_size=64, normalize_embeddings=True, show_progress_bar=False)
                np.savez_compressed(output / "scidocs_embeddings.npz", documents=documents, queries=queries,
                                    query_ids=np.array(ids), document_ids=np.array([str(d["_id"]) for d in docs]))
            for seed in SEEDS:
                print(f"Evaluation {dataset}, seed {seed}", flush=True)
                if dataset == "scidocs":
                    assignment = partition_documents(len(docs), 30, seed)
                    profiles = [build_profile(f"source_{i:03d}", documents[assignment == i], k=16, sigma=0,
                                rng=np.random.default_rng(seed + i), document_count=int(sum(assignment == i))) for i in range(30)]
                else:
                    assignment = np.load(REFERENCE / f"{dataset}_partition_{seed}.npy")
                    profiles = frozen_profiles(dataset, seed)
                np.save(output / f"{dataset}_partition_{seed}.npy", assignment)
                np.savez_compressed(output / f"{dataset}_profiles_{seed}.npz", **{p.source_id: p.centroids for p in profiles})
                prepared = center_profiles({p.source_id: p.centroids for p in profiles}, strength)
                evidence = {p.source_id: SourceEvidence(authorized=True, trust=1) for p in profiles}
                for position, (qid, query) in enumerate(zip(ids, queries)):
                    document_scores = documents @ query
                    tasks = [(b, m) for b in BUDGETS for m in ("raw_fixed", "centered_fixed", "old_relative", "centered_budget")]
                    tasks = tasks[position % len(tasks):] + tasks[:position % len(tasks)]
                    for budget, method in tasks:
                        start, trace = time.perf_counter(), None
                        if method == "raw_fixed":
                            selected = fixed_rank(score_profiles(query, profiles), budget)
                        elif method == "centered_fixed":
                            selected = fixed_rank(centered_scores(query, prepared), budget)
                        else:
                            cfg = relative_config(budget) if method == "old_relative" else budget_config(budget, strength)
                            trace = router.route(query, profiles, evidence, cfg)
                            selected = trace.selected_source_ids
                        row = dict(dataset=dataset, scenario="clean", method=method, budget=budget, seed=seed,
                                   query_id=qid, position=position, selected=selected, malicious_contact=0,
                                   routing_ms=(time.perf_counter() - start)*1000,
                                   budget_violation=int(len(selected) > budget or (trace is not None and trace.exposure_spent > budget)),
                                   stop_reason=trace.stop_reason if trace else "fixed_top_k",
                                   **clean_metrics(selected, qrels[qid], assignment, document_scores))
                        records.append(row)
                        stream.write(json.dumps(row) + "\n")
                for scenario in ("online_clean", "clone_empty", "clone_bait"):
                    for centered in (False, True):
                        for feedback in (False, True):
                            method = "relative_evidence" if feedback else "relative"
                            for row in attack_stream(queries, ids, qrels, documents, assignment, profiles, seed,
                                                     scenario, method, budget_config(3, strength, centered)):
                                row.update(dataset=dataset, method=("centered" if centered else "raw") +
                                           ("_trust" if feedback else "_neutral"))
                                records.append(row)
                                stream.write(json.dumps(row) + "\n")
                stream.flush()
    result = summarize(records)
    with (output / "summary.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(result[0]))
        writer.writeheader()
        writer.writerows(result)
    intervals = [paired_interval(records, d, b, "centered_budget", "raw_fixed", metric,
                                 bootstrap_seed=20260910)
                 for d in ("scifact", "nfcorpus", "scidocs") for b in BUDGETS
                 for metric in ("source_recall", "evidence_coverage", "document_recall_at_10", "contacts")]
    save_json(output / "intervals.json", intervals)
    save_json(output / "evaluation.json", dict(cases=len(records), inputs=inputs,
              budget_violations=sum(r["budget_violation"] for r in records), completed=True,
              results_sha256=fingerprint(output / "summary.csv")))
    print(f"Completed {len(records)} decisions", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["develop", "evaluate"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frozen", type=Path)
    args = parser.parse_args()
    if args.stage == "evaluate" and args.frozen is None:
        parser.error("evaluate requires --frozen")
    args.output.mkdir(parents=True, exist_ok=False)
    paths = [Path(__file__), ROOT / "backend/router/centering.py", ROOT / "backend/router/smart.py",
             ROOT / "backend/eval/run_routing_study.py", ROOT / "backend/eval/run_smart_pilot.py",
             ROOT / "backend/nodes/profile.py", ROOT / "docs/18-centered-routing-protocol.md"]
    for path in paths:
        destination = args.output / "snapshot" / path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
    artifacts = sorted(REFERENCE.glob("*.npz")) + sorted(REFERENCE.glob("*.npy"))
    save_json(args.output / "run-manifest.json", dict(stage=args.stage, started_at=time.time(),
              code={str(p.relative_to(ROOT)): fingerprint(p) for p in paths},
              reference={str(p.relative_to(ROOT)): fingerprint(p) for p in artifacts}))
    model = encoder()
    if args.stage == "develop":
        development(args.output, model)
    else:
        evaluate(args.output, model, args.frozen)


if __name__ == "__main__":
    main()
