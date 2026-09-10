"""Exploratory frozen-source acquisition comparison using cached embeddings."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import shutil

import numpy as np

from baselines.base import SourceProfile
from baselines.profile_fusion import run_control
from eval.prepare_answer_study import evidence_metrics
from eval.run_local_retrieval_study import REFERENCE, ROOT
from eval.run_smart_pilot import fingerprint
from nodes.document_retrieval import LocalRetrievalConfig, rerank_local
from router.discovery_completion import Passage, acquire, select_local
from router.evidence_budget import Candidate, prepare_profiles
from router.lexical_profile import VERSION, lexical_scores, fuse_scores


def normalized(text):
    return " ".join(re.findall(r"\w+", text.casefold()))


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    code = [Path(__file__), ROOT / "backend/router/discovery_completion.py",
            ROOT / "docs/33-discovery-completion-protocol.md"]
    manifest = dict(completed=False, exploratory=True, source_cap=3, candidate_cap=12,
                    code={str(p.relative_to(ROOT)): fingerprint(p) for p in code})
    for p in code:
        target = output / "snapshot" / p.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    original = json.loads((REFERENCE / "manifest.json").read_text())
    for name, digest in original["artifacts"].items():
        if fingerprint(REFERENCE / name) != digest:
            raise ValueError(f"changed cached artifact: {name}")
    question_path = next(Path(p) for p in original["inputs"] if p.endswith("/questions.jsonl"))
    questions = [json.loads(line) for line in question_path.open()]
    raw_path = question_path.parents[2] / "raw/multihop/MultiHopRAG.json"
    raw = json.loads(raw_path.read_text())
    lookup = {}
    for r in raw:
        key = normalized(r["query"])
        if key in lookup:
            raise ValueError("ambiguous raw question")
        lookup[key] = r
    manifest["inputs"] = {str(p):fingerprint(p) for p in (question_path, raw_path)}
    chunks = json.loads((REFERENCE / "chunks.json").read_text())
    parents = [c["document_id"] for c in chunks]
    text = [normalized(c["text"]) for c in chunks]
    with np.load(REFERENCE / "embeddings.npz") as z:
        vectors, queries = z["documents"], z["queries"]
        assert z["query_ids"].tolist() == [q["query_id"] for q in questions]
    sketches = json.loads((REFERENCE / "sketches.json").read_text())
    with np.load(REFERENCE / "profiles16.npz") as z:
        profiles = [SourceProfile(s,z[s],lexical_sketch=sketches[s],lexical_version=VERSION) for s in sorted(z.files)]
    pools = defaultdict(list)
    parent_chunks = defaultdict(list)
    for i,c in enumerate(chunks):
        pools[c["source_id"]].append(i)
        parent_chunks[c["document_id"]].append(i)
    rows, unmatched, total_facts = [], 0, 0
    with (output / "decisions.jsonl").open("w") as stream:
        for position,(question,query) in enumerate(zip(questions,queries)):
            raw_q = lookup[normalized(question["query"])]
            assert raw_q["answer"] == question["answer"]
            facts = [normalized(e["fact"]) for e in raw_q["evidence_list"] if normalized(e["fact"])]
            gold_pool = [i for d in question["evidence_doc_ids"] for i in parent_chunks[d]]
            matches = [{i for i in gold_pool if f in text[i]} for f in facts]
            unmatched += sum(not m for m in matches)
            total_facts += len(matches)
            scores = vectors @ query
            orders = {s:np.array(p)[np.argsort(-scores[p],kind="stable")] for s,p in pools.items()}
            _,_,semantic,_,_ = prepare_profiles(query,profiles)
            eligible = [p for p in profiles if p.source_id in semantic]
            fused = fuse_scores(semantic,lexical_scores(question["query"],eligible),"hybrid",.25)
            selected = sorted(fused,key=lambda s:(-fused[s],s))[:3]
            variants = {}
            for policy in ("cosine","parent_cap1"):
                ranks = {s:rerank_local(orders[s],scores,vectors,parents,LocalRetrievalConfig(policy)) for s in selected}
                def retrieve(s,offset):
                    if offset >= len(ranks[s]):
                        return None
                    i = int(ranks[s][offset])
                    return Candidate(s,str(i),chunks[i]["text"],vectors[i])
                r = run_control(query,question["query"],profiles,retrieve,"hybrid")
                variants["equal_"+policy] = ([int(p.document_id) for p in r.candidates],
                    [int(p.document_id) for p in r.final],r.to_dict())
            node_parents = {str(i):parents[i] for s in selected for i in orders[s]}
            node_orders = {s:[str(i) for i in orders[s]] for s in selected}
            def action(s,parent,seen,known):
                c = select_local(node_orders[s],node_parents,parent,seen,known)
                if c is None:
                    return None
                i = int(c)
                return Passage(s,c,parents[i],chunks[i]["text"],vectors[i])
            for completion in (False,True):
                r = acquire(question["query"],query,{s:fused[s] for s in selected},action,completion=completion)
                variants["discovery_completion" if completion else "discovery_only"] = (
                    [int(p.chunk_id) for p in r["candidates"]],[int(p.chunk_id) for p in r["final"]],r["actions"])
            for method,(candidate,final,trace) in variants.items():
                row = dict(query_id=question["query_id"],method=method,
                    **evidence_metrics([parents[i] for i in candidate],[parents[i] for i in final],question["evidence_doc_ids"]),
                    candidate_fact_coverage=sum(bool(m & set(candidate)) for m in matches)/len(matches) if matches else None,
                    final_fact_coverage=sum(bool(m & set(final)) for m in matches)/len(matches) if matches else None)
                actions = trace if isinstance(trace,list) else trace["actions"]
                assert len(actions)<=12 and len(candidate)<=12 and len(final)<=5
                row["requests"] = len(actions)
                rows.append(row)
                stream.write(json.dumps({**row,"trace":trace,"candidate_chunks":candidate,"final_chunks":final})+"\n")
            if (position+1)%500 == 0:
                print(f"{position+1}/{len(questions)}",flush=True)
    metrics = ("candidate_evidence_recall","final_evidence_recall","candidate_fact_coverage","final_fact_coverage","requests")
    summary = {method:{m:float(np.mean([r[m] for r in rows if r["method"]==method and r[m] is not None]))
                       for m in metrics} for method in variants}
    (output / "summary.json").write_text(json.dumps(summary,indent=2))
    manifest.update(completed=True,cases=len(rows),fact_instances=total_facts,
                    facts_not_literal_in_any_gold_chunk=unmatched,budget_violations=0,
                    artifacts={p.name:fingerprint(p) for p in output.iterdir() if p.is_file() and p.name!="manifest.json"})
    (output / "manifest.json").write_text(json.dumps(manifest,indent=2))
    print(json.dumps(summary,indent=2),flush=True)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    run(parser.parse_args().output.resolve())
