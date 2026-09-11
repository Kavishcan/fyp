"""E10: answer quality with local generation over routed, PSI-dispatched
evidence (docs/38).

Every result in docs/31–37 is a routing or transport measurement. This is
the first answer-level number: multiple-choice accuracy on MIRAGE
(Xiong et al., 2024 — medqa, medmcqa, pubmedqa, bioasq, mmlu-medical) with a
LOCAL model (Ollama, docs/03 target: the query and every passage stay on the
device), comparing

- closed_book   no passages; the model's own knowledge.
- psi           v2 local routing + PSI dispatch (privacy/psi.py, in-process
                nodes), `--top-per-node` passages from each contacted node,
                reranked on the device.
- broadcast     `--top-per-node` passages from EVERY node — the contact-
                everything reference, highest exposure.

Nodes: medical BEIR corpora (nfcorpus, scifact, trec-covid) plus
non-medical distractors (fiqa, arguana, scidocs) so routing has something to
get wrong; documents sampled as in eval/run_feb4rag.py and embedded with
bge-base. The same passages go to the generator in every condition that has
passages, so differences between psi and broadcast are routing, and
differences from closed_book are retrieval.

Accuracy is exact-match on the option letter the model returns. A model that
answers "the passages do not contain the answer" for an MCQ is scored as
wrong and counted separately as `abstained`. This is a small, single-model
measurement, not a benchmark result: MIRAGE's official setting retrieves
from MedRAG's PubMed/textbook corpora, which are not here, so the retrieval
condition is handicapped by the corpus, and that is stated.

Run: LLM_PROVIDER=ollama OLLAMA_MODEL=qwen3.5:9b python -m eval.run_answer_quality
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import time

import numpy as np

from eval.embed_cache import CachedEmbedder
from eval.run_feb4rag import sample_corpus
from eval.sweep import REPO_ROOT, RESULTS_DIR, HashingEmbedder, SentenceTransformerEmbedder, _normalise, build_node_profiles
from generation.ollama_generator import OllamaGenerator
from nodes.simulator import InProcessNode, attach_psi_index
from privacy.cluster_index import assign_clusters, rerank_passages
from privacy.psi import PSIClient
from router.v2 import V2Config, select_dispatch

MIRAGE = REPO_ROOT / "backend" / "vendor" / "ragroute" / "data" / "benchmark" / "MIRAGE.json"
LETTER_RE = re.compile(r"\b([A-D])\b")


def load_mirage(subsets: list[str], per_subset: int, seed: int) -> list[dict]:
    data = json.loads(MIRAGE.read_text())
    rng = random.Random(seed)
    out = []
    for subset in subsets:
        items = list(data[subset].items())
        rng.shuffle(items)
        for qid, item in items[:per_subset]:
            out.append({"subset": subset, "qid": qid, "question": item["question"],
                        "options": item["options"], "answer": item["answer"]})
    return out


def mcq_text(item: dict) -> str:
    options = "\n".join(f"{k}. {v}" for k, v in sorted(item["options"].items()))
    return (f"{item['question']}\n\nOptions:\n{options}\n\n"
            f"Choose the best option. Reply with the single option letter only.")


def parse_letter(answer: str, options: dict) -> str | None:
    text = answer.strip()
    m = re.match(r"^\(?([A-D])\)?[\.\):\s]", text + " ")
    if m and m.group(1) in options:
        return m.group(1)
    found = [x for x in LETTER_RE.findall(text) if x in options]
    return found[0] if found else None


def psi_passages(query_vec, node: InProcessNode, top_n: int, nprobe: int) -> list[str]:
    """Device-side PSI contact against an in-process node (no MCP)."""
    wanted = assign_clusters(query_vec, node.psi_centroids, nprobe=nprobe)
    q = PSIClient.blind(wanted)
    outputs = PSIClient.unblind(q, node.psi.evaluate(q.blinded))
    matches = PSIClient.open_matches(q, outputs, node.source_id, node.psi.envelopes_for(None))
    candidates = [p for cid in wanted for p in matches.get(cid, [])]
    return [doc for doc, _ in rerank_passages(query_vec, candidates, top_n=top_n)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--subsets", nargs="+", default=["medqa", "medmcqa", "pubmedqa", "bioasq", "mmlu"])
    parser.add_argument("--per-subset", type=int, default=30)
    parser.add_argument("--medical", nargs="+", default=["nfcorpus", "scifact", "trec-covid"])
    parser.add_argument("--distractors", nargs="+", default=["fiqa", "arguana", "scidocs"])
    parser.add_argument("--docs-per-engine", type=int, default=1500)
    parser.add_argument("--scan-lines", type=int, default=200_000)
    parser.add_argument("--max-nodes", type=int, default=6)
    parser.add_argument("--genuine-k", type=int, default=2)
    parser.add_argument("--coarse-k", type=int, default=12)
    parser.add_argument("--nprobe", type=int, default=2)
    parser.add_argument("--top-per-node", type=int, default=2)
    parser.add_argument("--conditions", nargs="+", default=["closed_book", "psi", "broadcast"])
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--model", default=None, help="Ollama model (default: OLLAMA_MODEL env)")
    parser.add_argument("--embedder", choices=["sentence-transformer", "hashing"], default="sentence-transformer")
    parser.add_argument("--embedder-model", default="BAAI/bge-base-en-v1.5")
    args = parser.parse_args()

    generator = OllamaGenerator(model=args.model)
    embedder = (CachedEmbedder(SentenceTransformerEmbedder(args.embedder_model))
                if args.embedder == "sentence-transformer" else HashingEmbedder())
    questions = load_mirage(args.subsets, args.per_subset, args.seed)
    print(f"model {generator.model}; {len(questions)} MIRAGE questions", flush=True)

    rng = random.Random(args.seed)
    engines = [*args.medical, *args.distractors]
    node_docs = {e: sample_corpus(e, args.docs_per_engine, args.scan_lines, rng) for e in engines}
    profiles = build_node_profiles(node_docs, embedder, k=3, seed=args.seed)
    nodes: dict[str, InProcessNode] = {}
    for e, docs in node_docs.items():
        emb = embedder.embed(docs)
        node = InProcessNode(e, docs, emb, routing_embeddings=emb)
        attach_psi_index(node, profiles[e], seed=args.seed)
        node.psi_centroids = profiles[e].cluster_centroids
        nodes[e] = node
    print(f"{len(nodes)} in-process nodes with PSI tables", flush=True)

    q_vecs = [_normalise(v) for v in embedder.embed([q["question"] for q in questions])]
    config = V2Config(exposure_budget=float(args.max_nodes), max_sources=args.max_nodes,
                      genuine_k=args.genuine_k, coarse_k=args.coarse_k, aggregation="max")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = time.strftime("%Y%m%d-%H%M%S")
    per_q: list[dict] = []
    for cond in args.conditions:
        started = time.perf_counter()
        for item, vec in zip(questions, q_vecs):
            if cond == "closed_book":
                passages, contacted = [], []
            elif cond == "broadcast":
                contacted = list(nodes)
                passages = [d for e in contacted for d in psi_passages(vec, nodes[e], args.top_per_node, args.nprobe)]
            else:
                decision = select_dispatch(vec, list(profiles.values()),
                                           trust={e: 0.5 for e in profiles}, per_source_cost={e: 1.0 for e in profiles},
                                           topic_key=item["subset"], config=config)
                contacted = decision.dispatched_source_ids
                passages = [d for e in contacted for d in psi_passages(vec, nodes[e], args.top_per_node, args.nprobe)]
            t = time.perf_counter()
            raw = generator.generate(mcq_text(item), passages)
            gen_ms = (time.perf_counter() - t) * 1000
            letter = parse_letter(raw, item["options"])
            per_q.append({"condition": cond, "subset": item["subset"], "qid": item["qid"],
                          "correct": 1.0 if letter == item["answer"] else 0.0,
                          "abstained": 1.0 if letter is None else 0.0,
                          "contacts": len(contacted), "medical_contacts": len([e for e in contacted if e in args.medical]),
                          "passages": len(passages), "generation_ms": gen_ms, "raw": raw[:200]})
        rows = [r for r in per_q if r["condition"] == cond]
        print(f"{cond:<12} acc {np.mean([r['correct'] for r in rows]):.3f} abstain {np.mean([r['abstained'] for r in rows]):.3f} "
              f"gen {np.mean([r['generation_ms'] for r in rows]):.0f}ms  ({time.perf_counter() - started:.0f}s)", flush=True)
        _write(RESULTS_DIR / f"answer_quality_{run_id}_per_question.csv", per_q)

    summary = []
    for cond in args.conditions:
        for subset in ["all", *args.subsets]:
            rows = [r for r in per_q if r["condition"] == cond and (subset == "all" or r["subset"] == subset)]
            if not rows:
                continue
            summary.append({"model": generator.model, "condition": cond, "subset": subset, "questions": len(rows),
                            "accuracy": float(np.mean([r["correct"] for r in rows])),
                            "abstained": float(np.mean([r["abstained"] for r in rows])),
                            "contacts": float(np.mean([r["contacts"] for r in rows])),
                            "medical_contacts": float(np.mean([r["medical_contacts"] for r in rows])),
                            "passages": float(np.mean([r["passages"] for r in rows])),
                            "generation_ms": float(np.mean([r["generation_ms"] for r in rows]))})
    out = RESULTS_DIR / f"answer_quality_{run_id}.csv"
    _write(out, summary)
    print(json.dumps(summary, indent=2))
    print(f"wrote {out}")


def _write(path, rows: list[dict]) -> None:
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
