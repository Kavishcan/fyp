"""Controlled local document-diversity audit, preserving frozen source routing."""
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
from eval.prepare_answer_study import evidence_metrics
from eval.run_candidate_study import save_json
from eval.run_smart_pilot import fingerprint
from eval.run_strong_controls import ROOT, CODE as PRIOR_CODE, transfer_tasks
from nodes.document_retrieval import LocalRetrievalConfig, rerank_local
from router.evidence_budget import Candidate
from router.lexical_profile import VERSION

REFERENCE = ROOT / "experiments/routing-study-answer-pilot-v1"
POLICIES = ("cosine", "parent_cap1", "parent_cap2", "mmr")


def run(output):
    output = output.resolve()
    original = json.loads((REFERENCE / "manifest.json").read_text())
    if not original["completed"]:
        raise ValueError("incomplete reference")
    for section, root in (("code", ROOT), ("artifacts", REFERENCE), ("inputs", Path("/"))):
        for name, digest in original[section].items():
            if fingerprint(root / name) != digest:
                raise ValueError(f"reference changed: {name}")
    code = list(dict.fromkeys(PRIOR_CODE + [Path(__file__), ROOT / "backend/nodes/document_retrieval.py",
        ROOT / "backend/nodes/simulator.py", ROOT / "backend/nodes/mcp_server.py",
        ROOT / "docs/30-local-retrieval-protocol.md"]))
    output.mkdir(parents=True, exist_ok=False)
    manifest = dict(completed=False, started_at=time.time(), code={str(p.relative_to(ROOT)): fingerprint(p) for p in code},
        reference_sha256=fingerprint(REFERENCE / "manifest.json"), policies=POLICIES,
        contact_cap=3, candidate_cap=12, final_k=5, pool_size=64, mmr_weight=.7,
        study="exploratory; previously inspected queries", generation_completed=False)
    for p in code:
        target = output / "snapshot" / p.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
    save_json(output / "manifest.json", manifest)
    chunks = json.loads((REFERENCE / "chunks.json").read_text())
    question_path = next(Path(p) for p in original["inputs"] if p.endswith("/questions.jsonl"))
    questions = [json.loads(line) for line in question_path.open()]
    parents = [c["document_id"] for c in chunks]
    with np.load(REFERENCE / "embeddings.npz") as z:
        vectors, queries = z["documents"], z["queries"]
        if z["query_ids"].tolist() != [q["query_id"] for q in questions] or len(vectors) != len(chunks):
            raise ValueError("embedding order mismatch")
    sketches = json.loads((REFERENCE / "sketches.json").read_text())
    profiles = {}
    for size in (16, 21):
        with np.load(REFERENCE / f"profiles{size}.npz") as z:
            profiles[size] = [SourceProfile(s, z[s], lexical_sketch=sketches[s] if size == 16 else "",
                                           lexical_version=VERSION if size == 16 else "") for s in sorted(z.files)]
    pools = defaultdict(list)
    for i, c in enumerate(chunks):
        pools[c["source_id"]].append(i)
    previous = {}
    for line in (REFERENCE / "retrieval.jsonl").open():
        r = json.loads(line)
        previous[r["query_id"], r["method"]] = r
    tasks = transfer_tasks(json.loads((REFERENCE / "frozen.json").read_text()))
    rows, ranking_costs = [], []
    with (output / "decisions.jsonl").open("w") as stream:
        for position, (question, query) in enumerate(zip(questions, queries)):
            scores = vectors @ query
            raw = {s: np.array(pool)[np.argsort(-scores[pool], kind="stable")] for s, pool in pools.items()}
            cache, contacts = {}, {}
            for method, weight, constant in tasks:
                for policy in POLICIES:
                    def retrieve(sid, offset):
                        key = sid, policy
                        if key not in cache:
                            start = time.perf_counter()
                            cache[key] = rerank_local(raw[sid], scores, vectors, parents, LocalRetrievalConfig(policy))
                            ranking_costs.append(dict(policy=policy, milliseconds=(time.perf_counter()-start)*1000))
                        ranking = cache[key]
                        if offset >= len(ranking):
                            return None
                        i = int(ranking[offset])
                        return Candidate(sid, str(i), chunks[i]["text"], vectors[i])

                    result = run_control(query, question["query"], profiles[21 if method == "semantic21" else 16],
                                         retrieve, method, weight, constant)
                    candidate_docs = [parents[int(p.document_id)] for p in result.candidates]
                    final_docs = [parents[int(p.document_id)] for p in result.final]
                    row = dict(query_id=question["query_id"], method=method, policy=policy,
                        **evidence_metrics(candidate_docs, final_docs, question["evidence_doc_ids"]),
                        contacts=len(result.contacted), requests=len(result.actions), returned=len(result.candidates),
                        unique_final_documents=len(set(final_docs)),
                        final_cosine=float(np.mean([scores[int(p.document_id)] for p in result.final])) if result.final else 0.,
                        budget_violation=int(len(result.contacted)>3 or len(result.actions)>12))
                    if policy == "cosine":
                        prior = previous[question["query_id"], method]
                        if result.to_dict()["final_document_ids"] != prior["trace"]["final_document_ids"] or any(
                            row[m] != prior[m] for m in ("candidate_evidence_recall", "final_evidence_recall")):
                            raise ValueError("cosine reproduction failed")
                        contacts[method] = result.contacted
                    elif result.contacted != contacts[method]:
                        raise ValueError("local policy changed source selection")
                    rows.append(row)
                    stream.write(json.dumps({**row, "final_documents": final_docs, "trace": result.to_dict()}) + "\n")
            if (position+1)%500 == 0:
                print(f"{position+1}/{len(questions)} queries", flush=True)
    summary, comparisons = [], []
    rng = np.random.default_rng(20260910)
    metrics = ("candidate_evidence_recall", "final_evidence_recall", "all_final_evidence", "unique_final_documents", "final_cosine")
    for method, _, _ in tasks:
        groups = {p: [r for r in rows if r["method"]==method and r["policy"]==p and r["final_evidence_recall"] is not None] for p in POLICIES}
        for policy, group in groups.items():
            summary.append(dict(method=method, policy=policy, evidence_questions=len(group),
                                **{m:float(np.mean([r[m] for r in group])) for m in metrics}))
            if policy == "cosine":
                continue
            for metric in ("candidate_evidence_recall", "final_evidence_recall", "all_final_evidence"):
                delta=np.array([a[metric]-b[metric] for a,b in zip(group,groups["cosine"])])
                boot=np.array([np.mean(rng.choice(delta,len(delta),replace=True)) for _ in range(10000)])
                comparisons.append(dict(method=method,policy=policy,metric=metric,difference=float(delta.mean()),
                    ci95=np.quantile(boot,[.025,.975]).tolist(), wins=int((delta>0).sum()),
                    ties=int((delta==0).sum()), losses=int((delta<0).sum())))
    with (output / "summary.csv").open("w") as f:
        writer=csv.DictWriter(f,fieldnames=list(summary[0])); writer.writeheader(); writer.writerows(summary)
    save_json(output / "comparisons.json", comparisons)
    save_json(output / "local-costs.json", {p:dict(computations=len(g:=[r for r in ranking_costs if r["policy"]==p]),
        mean_ms=float(np.mean([r["milliseconds"] for r in g]))) for p in POLICIES})
    manifest.update(completed=True,completed_at=time.time(),cases=len(rows),
        budget_violations=sum(r["budget_violation"] for r in rows),cosine_reproduced=True,contacts_unchanged=True,
        artifacts={p.name:fingerprint(p) for p in output.iterdir() if p.is_file() and p.name!="manifest.json"})
    save_json(output / "manifest.json",manifest)
    print(f"Completed {len(rows)} decisions, zero budget violations={manifest['budget_violations']==0}",flush=True)


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    run(p.parse_args().output)
