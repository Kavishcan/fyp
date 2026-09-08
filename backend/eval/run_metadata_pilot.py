"""Compare source metadata on frozen pilot inputs, without query-based profiling.

The same metadata builder is used by MCP nodes. Quality evaluation here uses
cached profiles/in-process routing, not real-network or privacy measurements.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import csv
import json
import os
from pathlib import Path
import platform
import sys
import time

import numpy as np

from baselines.base import SourceProfile
from eval.run_smart_pilot import fingerprint, measure_selection, summarize
from nodes.metadata import METHOD, describe_documents
from router.smart import SmartConfig, SmartRouter, SourceEvidence


def conditions(model: str) -> dict[str, SmartConfig]:
    configs = {}
    for mode, aggregations in [("centroid", ["mean", "max"]), ("description", ["mean"]),
                               ("combined", ["mean", "max"])]:
        for aggregation in aggregations:
            configs[f"{mode}_{aggregation}_fixed3"] = SmartConfig(
                relevance_mode=mode, aggregation=aggregation, query_model=model,
                description_weight=0.5, exposure_budget=3, max_sources=3,
                minimum_gain=0, redundancy_weight=0, uncertainty_penalty=0,
            )
    for mode in ("centroid", "description", "combined"):
        configs[f"{mode}_adaptive_b3"] = SmartConfig(
            relevance_mode=mode, query_model=model, exposure_budget=3, max_sources=5,
        )
    return configs


def fixed_metadata_ranking(query, profiles, config, top_k=3):
    """Fixed-contact diagnostic control, including zero-score ties.

    Unlike SmartRouter, a fixed top-k baseline does not abstain at zero gain.
    Positive-relevance ordering matches the equal-trust/no-overlap ablation.
    """
    query = np.asarray(query, dtype=float)
    query = query / (np.linalg.norm(query) or 1.0)
    scores = {}
    for profile in profiles:
        centroids = np.asarray(profile.centroids, dtype=float)
        norms = np.linalg.norm(centroids, axis=1, keepdims=True)
        centroids = np.divide(centroids, norms, out=np.zeros_like(centroids), where=norms != 0)
        similarities = np.clip(centroids @ query, 0, 1)
        score = float(np.mean(similarities) if config.aggregation == "mean" else np.max(similarities))
        if config.relevance_mode != "centroid":
            description = np.asarray(profile.description_embedding, dtype=float)
            description = description / (np.linalg.norm(description) or 1.0)
            metadata_score = float(np.clip(description @ query, 0, 1))
            score = metadata_score if config.relevance_mode == "description" else (
                (1 - config.description_weight) * score + config.description_weight * metadata_score)
        scores[profile.source_id] = score
    selected = sorted(scores, key=lambda sid: (-scores[sid], sid))[:top_k]
    return selected, scores


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Choose a fresh output directory")
    previous = json.loads((args.reference / "metadata.json").read_text())
    for file, expected in previous["files_sha256"].items():
        if fingerprint(Path(file)) != expected:
            raise ValueError(f"Input changed since reference pilot: {file}")
    corpus = Path(previous["corpus"])
    documents = [json.loads(line) for line in (corpus / "corpus.jsonl").open()]
    questions = {str(q["_id"]): q["text"] for q in map(json.loads, (corpus / "queries.jsonl").open())}
    document_index = {str(d["_id"]): i for i, d in enumerate(documents)}
    texts = [(d.get("title", "") + " " + d["text"]).strip() for d in documents]
    qrels = {}
    with (corpus / "qrels/test.tsv").open() as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            if float(row["score"]) > 0:
                qrels.setdefault(row["query-id"], set()).add(document_index[row["corpus-id"]])
    query_ids = sorted(qrels)
    if len(query_ids) != previous["unique_queries"]:
        raise ValueError("Query count differs from the reference")
    if not all(qid in questions for qid in query_ids):
        raise ValueError("Missing query text")
    with np.load(args.reference / "embeddings.npz") as frozen:
        document_embeddings, query_embeddings = frozen["documents"], frozen["queries"]
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from huggingface_hub import snapshot_download
    from sentence_transformers import SentenceTransformer
    import torch

    torch.set_num_threads(4)
    snapshot = Path(snapshot_download(previous["model"], local_files_only=True))
    if snapshot.name != previous["model_snapshot"]:
        raise ValueError("The cached model revision differs from the reference")
    model = SentenceTransformer(str(snapshot), local_files_only=True, device="cpu")
    configs = conditions(previous["model"])
    args.output.mkdir(parents=True)
    root = Path(__file__).resolve().parents[2]
    provenance = {
        "reference": str(args.reference.resolve()), "reference_metadata_sha256": fingerprint(args.reference / "metadata.json"),
        "model": previous["model"], "snapshot": snapshot.name, "metadata_method": METHOD,
        "max_topics": 16, "configuration": {name: asdict(config) for name, config in configs.items()},
        "command_argv": sys.argv, "platform": platform.platform(), "torch_threads": 4,
        "code_sha256": {str(p.relative_to(root)): fingerprint(p) for p in (
            Path(__file__), root / "backend/nodes/metadata.py", root / "backend/router/smart.py",
            root / "backend/nodes/profile.py", root / "backend/eval/run_smart_pilot.py")},
        "reference_artifact_sha256": {p.name: fingerprint(p) for p in args.reference.iterdir()
                                      if p.name.startswith(("embeddings", "profiles_", "partition_"))},
        "limits": ["Exploratory follow-up on previously inspected test queries; no new held-out validation claim",
                   "Descriptions derive from source documents only; no query/qrel-driven content or weight selection",
                   "Fixed3 disables adaptive stopping/overlap to isolate source-information effects",
                   "Fixed3 ranks clipped similarity scores, selecting zero-score ties by source ID if needed",
                   "Neutral trust, unit cost, no attacks, no generation, no MCP transport in quality benchmark",
                   "Metadata bytes are serialized profile payload sizes, not actual network traffic"],
    }
    records, payloads = [], []
    with (args.output / "decisions.jsonl").open("w") as stream:
        for seed in previous["partition_seeds"]:
            mapping = json.loads((args.reference / f"partition_{seed}.json").read_text())
            assignment = np.array([int(mapping[str(d["_id"])].rsplit("_", 1)[1]) for d in documents])
            source_ids = sorted(set(mapping.values()))
            metadata = [describe_documents([text for text, source in zip(texts, assignment)
                                             if source == int(sid.rsplit("_", 1)[1])]) for sid in source_ids]
            start = time.perf_counter()
            description_embeddings = model.encode([entry["description"] for entry in metadata],
                                                  normalize_embeddings=True, show_progress_bar=False)
            print(f"Seed {seed}: {len(metadata)} descriptions encoded in {time.perf_counter() - start:.2f}s", flush=True)
            profiles = []
            published = []
            with np.load(args.reference / f"profiles_{seed}.npz") as frozen:
                for sid, entry, vector in zip(source_ids, metadata, description_embeddings):
                    p = SourceProfile(sid, frozen[sid], **entry, description_embedding=vector,
                                      metadata_embedding_model=previous["model"])
                    profiles.append(p)
                    base = {"source_id": sid, "centroids": p.centroids.tolist()}
                    enriched = {**base, **entry, "description_embedding": vector.tolist(),
                                "metadata_embedding_model": previous["model"]}
                    payloads.append({"seed": seed, "source_id": sid,
                                     "base_bytes": len(json.dumps(base).encode()),
                                     "enriched_bytes": len(json.dumps(enriched).encode())})
                    published.append(enriched)
            (args.output / f"source_profiles_{seed}.json").write_text(json.dumps(published))
            evidence = {p.source_id: SourceEvidence(authorized=True) for p in profiles}
            router = SmartRouter()
            methods = list(configs)
            for index, (qid, query) in enumerate(zip(query_ids, query_embeddings)):
                doc_scores = document_embeddings @ query
                order = methods[index % len(methods):] + methods[:index % len(methods)]
                for name in order:
                    start = time.perf_counter()
                    if name.endswith("fixed3"):
                        ids, scores = fixed_metadata_ranking(query, profiles, configs[name])
                        trace = {"kind": "fixed_top3_control", "scores": scores}
                        exposure_spent = len(ids)
                    else:
                        decision = router.route(query, profiles, evidence, configs[name])
                        ids = decision.selected_source_ids
                        trace = decision.to_dict()
                        exposure_spent = decision.exposure_spent
                    routing_ms = (time.perf_counter() - start) * 1000
                    selected = [int(s.rsplit("_", 1)[1]) for s in ids]
                    # If this assertion fails, it is not a matched-contact comparison.
                    if name.endswith("fixed3") and len(selected) != 3:
                        raise ValueError(f"{name} did not select exactly three sources for {qid}")
                    row = {"query_id": qid, "seed": seed, "method": name, "routing_ms": routing_ms,
                           "budget_violation": exposure_spent > 3,
                           **measure_selection(selected, qrels[qid], assignment, doc_scores)}
                    records.append(row)
                    stream.write(json.dumps({**row, "selected": selected, "trace": trace}) + "\n")
            stream.flush()
    rows = summarize(records)
    with (args.output / "summary.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    provenance["payloads"] = payloads
    provenance["mean_metadata_extra_bytes"] = float(np.mean([p["enriched_bytes"] - p["base_bytes"] for p in payloads]))
    provenance["mean_base_bytes"] = float(np.mean([p["base_bytes"] for p in payloads]))
    (args.output / "metadata.json").write_text(json.dumps(provenance, indent=2))
    print(json.dumps(rows, indent=2), flush=True)
    print(f"Mean metadata bytes added per source: {provenance['mean_metadata_extra_bytes']:.0f}", flush=True)


if __name__ == "__main__":
    main()
