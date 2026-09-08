"""Offline real-data source-routing pilot, with no downloads or model training.

Random partitions are built without qrels. Embeddings/profiles are frozen across
methods. This is simulated federation: no MCP, generation or privacy attack.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path
import subprocess
import time

import numpy as np

from baselines.cosine_router import CosineRouter
from nodes.profile import build_profile
from router.smart import SmartConfig, SmartRouter, SourceEvidence


def fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def partition_documents(count: int, sources: int, seed: int) -> np.ndarray:
    if not 1 <= sources <= count:
        raise ValueError("sources must be between 1 and the document count")
    assignment = np.empty(count, dtype=int)
    for source, indices in enumerate(np.array_split(np.random.default_rng(seed).permutation(count), sources)):
        assignment[indices] = source
    return assignment


def measure_selection(selected, relevant_docs, assignment, document_scores, top_n=10):
    relevant_sources = set(assignment[list(relevant_docs)].tolist())
    selected_set = set(selected)
    available = np.flatnonzero(np.isin(assignment, selected))
    order = np.argsort(-document_scores[available], kind="stable")[:top_n]
    retrieved = set(available[order].tolist())
    return {
        "contacts": len(selected),
        "source_recall": len(selected_set & relevant_sources) / len(relevant_sources),
        "document_recall_at_10": len(retrieved & relevant_docs) / len(relevant_docs),
        "irrelevant_contacts": len(selected_set - relevant_sources),
    }


def summarize(records):
    result = []
    for method in sorted({r["method"] for r in records}):
        rows = [r for r in records if r["method"] == method]
        seeds = sorted({r["seed"] for r in rows})
        seed_recalls = [np.mean([r["source_recall"] for r in rows if r["seed"] == seed]) for seed in seeds]
        item = {"method": method, "query_partition_cases": len(rows)}
        for metric in ("contacts", "source_recall", "document_recall_at_10", "irrelevant_contacts"):
            item[metric] = float(np.mean([r[metric] for r in rows]))
        item.update({
            "source_recall_seed_min": float(min(seed_recalls)),
            "source_recall_seed_max": float(max(seed_recalls)),
            "routing_median_ms": float(np.median([r["routing_ms"] for r in rows])),
            "routing_p95_ms": float(np.percentile([r["routing_ms"] for r in rows], 95)),
            "empty_selection_rate": sum(r["contacts"] == 0 for r in rows) / len(rows),
            "budget_violations": sum(r["budget_violation"] for r in rows),
        })
        result.append(item)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sources", type=int, default=30)
    parser.add_argument("--seeds", type=int, nargs="+", default=[11, 22, 33])
    parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Choose a new output directory; existing results are never overwritten")

    corpus_path = args.corpus / "corpus.jsonl"
    queries_path = args.corpus / "queries.jsonl"
    qrels_path = args.corpus / "qrels" / "test.tsv"
    with corpus_path.open() as stream:
        documents = [json.loads(line) for line in stream]
    document_index = {str(doc["_id"]): i for i, doc in enumerate(documents)}
    if len(document_index) != len(documents):
        raise ValueError("Duplicate document IDs")
    qrels = {}
    with qrels_path.open() as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            if float(row["score"]) > 0:
                qrels.setdefault(row["query-id"], set()).add(document_index[row["corpus-id"]])
    with queries_path.open() as stream:
        questions = {str(q["_id"]): q["text"] for q in map(json.loads, stream)}
    query_ids = sorted(qrels)
    query_texts = [questions[qid] for qid in query_ids]
    document_texts = [(doc.get("title", "") + " " + doc["text"]).strip() for doc in documents]

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from huggingface_hub import snapshot_download
    from sentence_transformers import SentenceTransformer
    import torch

    torch.set_num_threads(4)
    snapshot = Path(snapshot_download(args.model, local_files_only=True))
    model = SentenceTransformer(str(snapshot), local_files_only=True, device="cpu")
    args.output.mkdir(parents=True)
    started = time.perf_counter()
    print(f"Encoding {len(documents)} documents and {len(query_ids)} test questions; CPU/offline", flush=True)
    document_embeddings = model.encode(document_texts, batch_size=64, normalize_embeddings=True, show_progress_bar=False)
    query_embeddings = model.encode(query_texts, batch_size=64, normalize_embeddings=True, show_progress_bar=False)
    embedding_seconds = time.perf_counter() - started
    print(f"Encoding completed in {embedding_seconds:.1f}s", flush=True)
    np.savez_compressed(args.output / "embeddings.npz", documents=document_embeddings, queries=query_embeddings)

    configs = {f"smart_budget_{budget}": SmartConfig(exposure_budget=budget, max_sources=5) for budget in (1, 3, 5)}
    configs["smart_no_overlap_b3"] = SmartConfig(exposure_budget=3, max_sources=5, redundancy_weight=0)
    configs["smart_zero_gain_b3"] = SmartConfig(exposure_budget=3, max_sources=5, minimum_gain=0)
    configs["smart_no_uncertainty_b3"] = SmartConfig(exposure_budget=3, max_sources=5, uncertainty_penalty=0)
    root = Path(__file__).resolve().parents[2]
    metadata = {
        "corpus": str(args.corpus.resolve()), "documents": len(documents), "unique_queries": len(query_ids),
        "source_count": args.sources, "partition_seeds": args.seeds,
        "partition": "balanced random document shards, independent of queries/qrels",
        "model": args.model, "model_snapshot": snapshot.name,
        "model_max_sequence_length": model.max_seq_length,
        "embedding_seconds": embedding_seconds, "device": "cpu", "torch_threads": 4,
        "centroids_per_source": 4, "profile_noise": 0, "profile_iterations": 50,
        "source_trust": "neutral 0.5; no feedback in this isolated selection pilot",
        "exposure_cost": "one unit per selected simulated source", "smart_configs": {k: asdict(v) for k, v in configs.items()},
        "files_sha256": {str(p): fingerprint(p) for p in (corpus_path, queries_path, qrels_path)},
        "code_sha256": {str(p.relative_to(root)): fingerprint(p) for p in (
            Path(__file__), root / "backend/router/smart.py", root / "backend/nodes/profile.py",
            root / "backend/baselines/cosine_router.py")},
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "git_status": subprocess.check_output(["git", "status", "--short"], cwd=root, text=True),
        "versions": {name: version(name) for name in ("numpy", "torch", "sentence-transformers")},
        "limits": ["No MCP transport, generation or attack evaluation", "No parameter tuning; defaults and predeclared ablations",
                   "Source recall uses positive qrels; unjudged documents may also be relevant",
                   "Whole-document embeddings may truncate long texts", "Routing latency excludes embedding/profile/retrieval time",
                   "Repeated partitions share test queries and documents; not independent query samples"],
    }
    (args.output / "metadata.json").write_text(json.dumps(metadata, indent=2))
    records = []
    with (args.output / "decisions.jsonl").open("w") as raw:
        for seed in args.seeds:
            assignment = partition_documents(len(documents), args.sources, seed)
            (args.output / f"partition_{seed}.json").write_text(json.dumps({
                str(doc["_id"]): f"source_{assignment[i]:03d}" for i, doc in enumerate(documents)
            }))
            profiles = [build_profile(
                f"source_{i:03d}", document_embeddings[assignment == i], k=4, sigma=0,
                rng=np.random.default_rng(seed + i), document_count=int(sum(assignment == i)),
            ) for i in range(args.sources)]
            np.savez_compressed(args.output / f"profiles_{seed}.npz", **{p.source_id: p.centroids for p in profiles})
            routers = {aggregation: CosineRouter(aggregation=aggregation) for aggregation in ("mean", "max")}
            for router in routers.values():
                router.register_sources(profiles)
            evidence = {p.source_id: SourceEvidence(authorized=True) for p in profiles}
            smart = SmartRouter()
            methods = ["broadcast", "cosine_mean_1", "cosine_mean_3", "cosine_mean_5", "cosine_max_3", *configs]
            print(f"Seed {seed}: scoring {len(query_ids)} queries across {len(methods)} conditions", flush=True)
            for index, (qid, query) in enumerate(zip(query_ids, query_embeddings)):
                document_scores = document_embeddings @ query
                # Rotate method order to reduce systematic first-method timing bias.
                order = methods[index % len(methods):] + methods[:index % len(methods)]
                for method in order:
                    budget = None
                    trace = None
                    start = time.perf_counter()
                    if method == "broadcast":
                        selected = list(range(args.sources))
                    elif method.startswith("cosine"):
                        _, aggregation, k = method.split("_")
                        ranking = routers[aggregation].rank(query, int(k))
                        selected = [int(s.rsplit("_", 1)[1]) for s in ranking.ranked_source_ids]
                    else:
                        config = configs[method]
                        decision = smart.route(query, profiles, evidence, config)
                        selected = [int(s.rsplit("_", 1)[1]) for s in decision.selected_source_ids]
                        budget = config.exposure_budget
                        trace = decision.to_dict()
                    elapsed = (time.perf_counter() - start) * 1000
                    row = {"query_id": qid, "seed": seed, "method": method, "routing_ms": elapsed,
                           "budget_violation": budget is not None and len(selected) > budget,
                           **measure_selection(selected, qrels[qid], assignment, document_scores)}
                    records.append(row)
                    raw.write(json.dumps({**row, "selected": selected, "trace": trace}) + "\n")
            raw.flush()
    rows = summarize(records)
    with (args.output / "summary.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(rows, indent=2), flush=True)


if __name__ == "__main__":
    main()
