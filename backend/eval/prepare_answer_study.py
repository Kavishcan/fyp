"""Local MultiHop-RAG retrieval study and reproducible, ungenerated answer requests."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from baselines.base import SourceProfile
from baselines.profile_fusion import run_control
from eval.run_candidate_study import save_json
from eval.run_centered_study import encoder
from eval.run_rich_profile_study import cluster
from eval.run_smart_pilot import fingerprint
from eval.run_strong_controls import frozen_config, start_manifest, transfer_tasks
from generation.base import build_prompt
from router.evidence_budget import Candidate
from router.lexical_profile import build_sketch, VERSION, BYTES


def token_chunks(text, tokenizer, size=180, overlap=30):
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("invalid chunk settings")
    tokens = tokenizer.encode(text, add_special_tokens=False)
    for i in range(0, len(tokens), size - overlap):
        yield tokenizer.decode(tokens[i:i + size], skip_special_tokens=True)
        if i + size >= len(tokens):
            break


def capped_text(text, tokenizer, cap=256):
    if cap < 1:
        raise ValueError("invalid token cap")
    tokens = tokenizer.encode(text, add_special_tokens=False)[:cap]
    result = tokenizer.decode(tokens, skip_special_tokens=True)
    # Some tokenizers do not round-trip decode/encode exactly.
    while len(tokenizer.encode(result, add_special_tokens=False)) > cap:
        tokens = tokens[:-1]
        result = tokenizer.decode(tokens, skip_special_tokens=True)
    return result


def evidence_metrics(candidate_docs, final_docs, relevant):
    relevant = set(relevant)
    if not relevant:
        return dict(candidate_evidence_recall=None, final_evidence_recall=None,
                    all_candidate_evidence=None, all_final_evidence=None)
    return dict(candidate_evidence_recall=len(set(candidate_docs) & relevant) / len(relevant),
                final_evidence_recall=len(set(final_docs) & relevant) / len(relevant),
                all_candidate_evidence=int(relevant <= set(candidate_docs)),
                all_final_evidence=int(relevant <= set(final_docs)))


def pilot_questions(questions, count=24):
    ids = [q["query_id"] for q in questions]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate question IDs")
    return sorted(ids, key=lambda q: (hashlib.sha256(q.encode()).hexdigest(), q))[:count]


def run(dataset, output, frozen_path):
    frozen = frozen_config(frozen_path)
    dataset, output = dataset.resolve(), output.resolve()
    manifest = start_manifest(output, "multihop-answer-preparation")
    manifest["study"] = "exploratory MultiHop-RAG transfer; generation pending"
    manifest["frozen_sha256"] = fingerprint(frozen_path)
    save_json(output / "frozen.json", frozen)
    corpus_paths = sorted((dataset / "clients").glob("*/corpus.jsonl"))
    questions_path = dataset / "questions.jsonl"
    manifest["inputs"] = {str(p): fingerprint(p) for p in corpus_paths + [questions_path]}
    documents, source_docs, seen = [], defaultdict(list), set()
    for path in corpus_paths:
        with path.open() as f:
            for doc in map(json.loads, f):
                if doc["doc_id"] in seen or doc["client_id"] != path.parent.name:
                    raise ValueError("duplicate document or inconsistent source")
                seen.add(doc["doc_id"])
                documents.append(doc)
                source_docs[doc["client_id"]].append(doc)
    with questions_path.open() as f:
        questions = list(map(json.loads, f))
    pilot = set(pilot_questions(questions))
    if not documents or not questions:
        raise ValueError("empty dataset")
    for question in questions:
        if not isinstance(question["answer"], str) or not question["answer"].strip():
            raise ValueError("missing answer label")
        if set(question["evidence_doc_ids"]) - seen:
            raise ValueError("missing gold documents; must not silently discard")
    model = encoder()
    tokenizer = model.tokenizer
    chunks, by_source = [], defaultdict(list)
    for doc in documents:
        for text in token_chunks((doc.get("title", "") + " " + doc["body"]).strip(), tokenizer):
            by_source[doc["client_id"]].append(len(chunks))
            chunks.append(dict(document_id=doc["doc_id"], source_id=doc["client_id"], text=text))
    print(f"MultiHop: {len(documents)} documents, {len(chunks)} chunks, {len(source_docs)} sources, {len(questions)} queries", flush=True)
    vectors = model.encode([c["text"] for c in chunks], batch_size=64, normalize_embeddings=True, show_progress_bar=False)
    queries = model.encode([q["query"] for q in questions], batch_size=64, normalize_embeddings=True, show_progress_bar=False)
    np.savez_compressed(output / "embeddings.npz", documents=vectors, queries=queries,
                        query_ids=np.array([q["query_id"] for q in questions]))
    save_json(output / "chunks.json", chunks)
    p16, p21, costs = [], [], []
    for i, sid in enumerate(sorted(source_docs)):
        indices = by_source[sid]
        sketch = build_sketch([d.get("title", "") + " " + d["body"] for d in source_docs[sid]])
        c16 = cluster(vectors[indices], 16, 11 + i)[1].astype(np.float32)
        c21 = cluster(vectors[indices], 21, 11 + i)[1].astype(np.float32)
        p16.append(SourceProfile(sid, c16, lexical_sketch=sketch, lexical_version=VERSION))
        p21.append(SourceProfile(sid, c21))
        costs.append(dict(source_id=sid, documents=len(source_docs[sid]), chunks=len(indices),
                          centroids16=len(c16), centroids21=len(c21), hybrid_bytes=c16.nbytes + BYTES,
                          semantic16_bytes=c16.nbytes, semantic21_bytes=c21.nbytes))
    save_json(output / "profile-costs.json", costs)
    np.savez_compressed(output / "profiles16.npz", **{p.source_id: p.centroids for p in p16})
    np.savez_compressed(output / "profiles21.npz", **{p.source_id: p.centroids for p in p21})
    save_json(output / "sketches.json", {p.source_id: p.lexical_sketch for p in p16})
    tasks = transfer_tasks(frozen)
    rows, requests, references = [], [], []

    def add_request(question, method, final):
        passages = [capped_text(p.document, tokenizer) for p in final]
        counts = [len(tokenizer.encode(p, add_special_tokens=False)) for p in passages]
        if len(passages) > 5 or sum(counts) > 1280:
            raise ValueError("context cap exceeded")
        requests.append(dict(query_id=question["query_id"], method=method,
                             prompt=build_prompt(question["query"], passages),
                             chunk_ids=[p.document_id for p in final], context_tokens=sum(counts),
                             tokenizer="cached MiniLM tokenizer, not generator tokenizer"))
        references.append(dict(query_id=question["query_id"], method=method, answers=[question["answer"]]))

    with (output / "retrieval.jsonl").open("w") as stream:
        for position, (question, query) in enumerate(zip(questions, queries)):
            scores = vectors @ query
            rankings = {s: np.array(pool)[np.argsort(-scores[pool], kind="stable")[:12]] for s, pool in by_source.items()}

            def retrieve(sid, offset):
                if offset >= len(rankings[sid]):
                    return None
                i = int(rankings[sid][offset])
                return Candidate(sid, str(i), chunks[i]["text"], vectors[i])

            for method, weight, constant in tasks:
                result = run_control(query, question["query"], p21 if method == "semantic21" else p16,
                                     retrieve, method, weight, constant)
                candidate_docs = [chunks[int(p.document_id)]["document_id"] for p in result.candidates]
                final_docs = [chunks[int(p.document_id)]["document_id"] for p in result.final]
                row = dict(query_id=question["query_id"], method=method, question_type=question.get("question_type"),
                           contacts=len(result.contacted), requests=len(result.actions), returned=len(result.candidates),
                           **evidence_metrics(candidate_docs, final_docs, question["evidence_doc_ids"]),
                           budget_violation=int(len(result.contacted) > 3 or len(result.actions) > 12))
                rows.append(row)
                stream.write(json.dumps({**row, "candidate_documents": candidate_docs, "final_documents": final_docs,
                                         "trace": result.to_dict()}) + "\n")
                if question["query_id"] in pilot:
                    add_request(question, method, result.final)
            if question["query_id"] in pilot:
                add_request(question, "no_retrieval", [])
            if (position + 1) % 500 == 0:
                print(f"  MultiHop {position + 1}/{len(questions)}", flush=True)
    for name, data in (("answer-requests.jsonl", requests), ("answer-references.jsonl", references)):
        with (output / name).open("w") as stream:
            for row in data:
                stream.write(json.dumps(row) + "\n")
    summary = []
    for method, _, _ in tasks:
        all_rows = [r for r in rows if r["method"] == method]
        judged = [r for r in all_rows if r["candidate_evidence_recall"] is not None]
        summary.append(dict(method=method, questions=len(all_rows), evidence_questions=len(judged),
                            no_evidence_questions=len(all_rows) - len(judged),
                            **{m: float(np.mean([r[m] for r in judged])) if judged else None for m in
                               ("candidate_evidence_recall", "final_evidence_recall", "all_candidate_evidence", "all_final_evidence")},
                            **{m: float(np.mean([r[m] for r in all_rows])) for m in ("contacts", "requests", "returned")}))
    save_json(output / "retrieval-summary.json", summary)
    save_json(output / "generation-status.json", dict(status="pending", calls_made=0,
              reason="No authorized generation run performed; requests/references ready for a fixed-model pilot.",
              query_count=len(pilot), request_count=len(requests)))
    manifest.update(completed=True, completed_at=time.time(), documents=len(documents), sources=len(source_docs),
                    chunks=len(chunks), questions=len(questions), cases=len(rows),
                    budget_violations=sum(r["budget_violation"] for r in rows),
                    generation_completed=False,
                    snapshot=json.loads((frozen_path.parent / "manifest.json").read_text())["snapshot"],
                    embedding_model="sentence-transformers/all-MiniLM-L6-v2", max_sequence_length=256,
                    artifacts={p.name: fingerprint(p) for p in output.iterdir() if p.is_file() and p.name != "manifest.json"})
    save_json(output / "manifest.json", manifest)
    print(f"Prepared {len(requests)} answer requests; no generated answers or answer-quality results", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--frozen", type=Path, required=True)
    a = p.parse_args()
    run(a.dataset, a.output, a.frozen)
