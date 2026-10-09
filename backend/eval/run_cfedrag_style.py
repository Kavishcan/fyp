"""C-FedRAG-style evaluation: MIRAGE PubMedQA + BioASQ answer accuracy, with
the privacy and cost columns C-FedRAG does not report (docs/57).

C-FedRAG (Addison et al., 2024, arXiv 2412.13163, p.6-7) evaluates answer
accuracy on MIRAGE's PubMedQA (500 yes/no/maybe) and BioASQ (618 yes/no)
questions, retrieving from MedRAG corpora split over two sites, top-8 chunks
per corpus re-ranked to a context of 8, Llama-3-8B. This harness keeps the
question sets, the 2-site layout and the 8-chunk context, and changes:

- corpus: a PubMed subset built from NCBI (eval/build_pubmed_subset.py:
  every question's source abstract plus ~20 relevance-ranked distractors per
  question) and MedRAG Textbooks narrowed the way C-FedRAG narrowed each
  corpus, the top `--textbook-per-question` BM25 snippets per question.
  StatPearls (2 GB) and Wikipedia are not used.
- generator: the local Qwen3.5-9B (Ollama, thinking off, temperature 0),
  the model of docs/38 and docs/50. Absolute accuracy is NOT comparable to
  C-FedRAG's published numbers; conditions are compared within one run.
- ranking: dense bge-base cosine everywhere (no cross-encoder), so ranking
  differences between conditions come from what each design can reach.
- prompt: this harness's own (see `prompt`): documents, then the question,
  options and "one letter only" last; answers capped at 16 tokens. Retrieval
  is timed for all questions first, then answers are generated, so model
  load does not inflate retrieval times.

Conditions (all return 8 passages unless closed-book):
- closed_book    no retrieval.
- centralized    one index over every snippet; a single server holds the
                 data and reads the question.
- broadcast      C-FedRAG's evaluated setup (p.5) without the enclave: the
                 question goes to every site, each returns its local top-8,
                 the coordinator keeps the best 8. With exact dense search
                 this ranks identically to centralized; it differs in
                 exposure and cost.
- selective      a selective router (C-FedRAG's proposed improvement, p.4;
                 RAGRoute's approach): the 2 sites whose best published
                 cluster centroid is closest receive the question.
- fedsafe_P{P}   FedSafeRAG (privacy/blind_unlock.py): tables downloaded
                 once, the device unlocks the P best clusters across all
                 sites with exactly P real-or-dummy blinded points at every
                 site, ranks the unlocked records and keeps 8. Sites hold
                 rule-de-identified text (docs/44).

Topologies: `2site` (Site 1 PubMed, Site 2 Textbooks, as C-FedRAG's two
sites) and `8hosp` (spherical k-means of all snippets into 8 hospitals, the
docs/46 method). Topic leakage needs `8hosp`: the topic of a question is the
hospital holding its source abstract; a naive-Bayes observer trained on the
first half of the questions' contact patterns guesses the second half,
against the majority-class floor (attacks/a2_topic_inference.py).

Per question: correct / abstained, source abstract among the 8 passages
(gold@8), sites that read the question, records released (text that leaves
a site), bytes up and down, measured device and site compute, modelled
retrieval latency (device + slowest of RTT + site time + bytes / bandwidth,
contacts in parallel; `--rtt-ms`, `--mbps`, as docs/53), generation time
from the wall clock. Identical passage lists reuse the earlier answer
(temperature 0 gives the same output) and are flagged `reused`.

Results append to results/cfedrag_style_<run_id>_per_question.jsonl after
every question; `--run-id` resumes an interrupted run.

Run: python -m eval.run_cfedrag_style --topology 8hosp
     (pilot: --per-subset 25)
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import time
from collections import Counter

import numpy as np

from attacks.a2_topic_inference import HistoryAttacker, evaluate
from eval.embed_cache import CachedEmbedder
from eval.run_answer_quality import parse_letter
from eval.sweep import REPO_ROOT, RESULTS_DIR, SentenceTransformerEmbedder
from nodes.simulator import build_simulated_source
from privacy.blind_unlock import NodeClusters, TableCache, plan_probes, unlock
from privacy.cluster_index import kmeans_unit, rerank_passages

MIRAGE = REPO_ROOT / "backend" / "vendor" / "ragroute" / "data" / "benchmark" / "MIRAGE.json"
PUBMED = REPO_ROOT / "backend" / "vendor" / "pubmed_subset" / "pubmed_subset.jsonl"
TEXTBOOKS = REPO_ROOT / "backend" / "vendor" / "medrag_textbooks" / "chunk"
CONTEXT = 8
MAX_ANSWER_TOKENS = 16


def prompt(item: dict, passages: list[str]) -> str:
    """The harness's own template (generation/base.py's fixed template asks
    the model to answer from the passages only, which made closed-book
    default to "no"/"maybe" in the pilot). The instruction comes after the
    passages so long contexts do not bury it. Closed-book gets the question
    alone, like C-FedRAG's no-retrieval baseline."""
    options = "\n".join(f"{k}. {v}" for k, v in sorted(item["options"].items()))
    letters = ", ".join(sorted(item["options"]))
    head = ("Relevant documents:\n" + "\n".join(f"[{i + 1}] {p}" for i, p in enumerate(passages)) + "\n\n"
            if passages else "")
    return (f"{head}Answer the following medical question"
            f"{' using the documents above and your own knowledge' if passages else ''}.\n\n"
            f"Question: {item['question']}\nOptions:\n{options}\n\n"
            f"Reply with one letter only ({letters}).\nAnswer:")


def load_questions(subsets: list[str], per_subset: int, seed: int) -> list[dict]:
    data = json.loads(MIRAGE.read_text())
    out = []
    for subset in subsets:
        items = sorted(data[subset].items())
        if per_subset:
            random.Random(seed).shuffle(items)
            items = items[:per_subset]
        for qid, item in items:
            out.append({"subset": subset, "qid": qid, "question": item["question"], "options": item["options"],
                        "answer": item["answer"], "gold": {f"pubmed_{p}" for p in item.get("PMID", [])}})
    random.Random(seed).shuffle(out)       # mixes subsets, so both halves of the leakage split hold both
    return out


def load_pubmed() -> dict[str, str]:
    docs = {}
    with open(PUBMED) as handle:
        for line in handle:
            r = json.loads(line)
            docs[r["id"]] = f"{r['title']} {r['content']}".strip()
    return docs


def select_textbooks(questions: list[dict], per_question: int) -> dict[str, str]:
    """C-FedRAG kept the top-scoring snippets of each corpus per task; here the
    top `per_question` Okapi BM25 snippets of each question, unioned."""
    from sklearn.feature_extraction.text import CountVectorizer

    ids, texts = [], []
    for path in sorted(TEXTBOOKS.glob("*.jsonl")):
        with open(path) as handle:
            for line in handle:
                r = json.loads(line)
                ids.append(r["id"])
                texts.append(r["content"])
    cv = CountVectorizer(stop_words="english")
    tf = cv.fit_transform(texts).tocsr().astype(np.float64)
    n_docs = tf.shape[0]
    df = np.bincount(tf.indices, minlength=tf.shape[1])
    idf = np.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)
    dl = np.asarray(tf.sum(axis=1)).ravel()
    k1, b = 1.2, 0.75
    norm = k1 * (1 - b + b * dl / dl.mean())
    rows = np.repeat(np.arange(n_docs), np.diff(tf.indptr))
    tf.data = idf[tf.indices] * tf.data * (k1 + 1) / (tf.data + norm[rows])
    q = cv.transform([x["question"] for x in questions])
    q.data[:] = 1.0
    chosen: set[int] = set()
    for start in range(0, q.shape[0], 64):
        scores = (q[start:start + 64] @ tf.T).toarray()
        top = np.argpartition(-scores, per_question, axis=1)[:, :per_question]
        chosen.update(int(j) for j in top.ravel())
    return {ids[j]: texts[j] for j in sorted(chosen)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--subsets", nargs="+", default=["pubmedqa", "bioasq"])
    parser.add_argument("--per-subset", type=int, default=0, help="0 = every question")
    parser.add_argument("--topology", choices=["2site", "8hosp"], default="8hosp")
    parser.add_argument("--textbook-per-question", type=int, default=20)
    parser.add_argument("--probes", nargs="+", type=int, default=[8, 24])
    parser.add_argument("--selective-k", type=int, default=2)
    parser.add_argument("--generate", nargs="*", default=None,
                        help="conditions that call the generator (default: all); the rest are retrieval-only")
    parser.add_argument("--model", default=None, help="Ollama model (default: OLLAMA_MODEL env)")
    parser.add_argument("--embedder-model", default="BAAI/bge-base-en-v1.5")
    parser.add_argument("--rtt-ms", type=float, default=40.0)
    parser.add_argument("--mbps", type=float, default=100.0)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--run-id", default=None, help="resume this run (skips questions already written)")
    args = parser.parse_args()

    t0 = time.perf_counter()
    questions = load_questions(args.subsets, args.per_subset, args.seed)
    pubmed = load_pubmed()
    textbooks = select_textbooks(questions, args.textbook_per_question)
    corpus = {**pubmed, **textbooks}
    print(f"{len(questions)} questions; corpus {len(pubmed)} PubMed + {len(textbooks)} Textbooks snippets "
          f"({time.perf_counter() - t0:.0f}s)", flush=True)
    missing = sum(1 for x in questions if not (x["gold"] & pubmed.keys()))
    print(f"questions whose source abstract is not in the corpus: {missing}", flush=True)

    embedder = CachedEmbedder(SentenceTransformerEmbedder(args.embedder_model))
    ids = list(corpus)
    vecs = embedder.embed([corpus[d] for d in ids])
    vecs = vecs / np.maximum(np.linalg.norm(vecs, axis=1, keepdims=True), 1e-12)
    print(f"embedded {len(ids)} snippets ({time.perf_counter() - t0:.0f}s)", flush=True)

    if args.topology == "2site":
        site_of = {d: ("site1_pubmed" if d.startswith("pubmed_") else "site2_textbooks") for d in ids}
    else:
        _, assign = kmeans_unit(vecs, 8, args.seed)
        site_of = {d: f"hospital_{int(a)}" for d, a in zip(ids, assign.tolist())}
    sites = sorted(set(site_of.values()))
    site_docs: dict[str, list[str]] = {s: [] for s in sites}
    for d in ids:
        site_docs[site_of[d]].append(d)
    print(f"sites: {dict(sorted(Counter(site_of.values()).items()))}", flush=True)
    # Topic of a question = the site holding its source abstract(s); None when
    # the abstract has no text in PubMed (then it is left out of the leakage test).
    topic_of = [Counter(site_of[g] for g in x["gold"] if g in site_of).most_common(1)[0][0]
                if x["gold"] & site_of.keys() else None for x in questions]

    # Raw sites (broadcast / selective: they read the question and search their
    # own text) and FedSafeRAG sites (rule de-identification at load, cluster
    # tables, OPRF keys). Same snippets; embeddings come from the cache.
    raw, fed = {}, {}
    for i, s in enumerate(sites):
        texts = [corpus[d] for d in site_docs[s]]
        node, _ = build_simulated_source(s, texts, embedder, k=3, sigma=0.0, rng=np.random.default_rng(args.seed + i),
                                         deidentify=False, psi=False)
        raw[s] = (node, dict(zip(node.documents, site_docs[s])))
        node, profile = build_simulated_source(s, texts, embedder, k=3, sigma=0.0,
                                               rng=np.random.default_rng(args.seed + i), deidentify=True)
        node.psi.blind_embedding_dtype = "int8"
        fed[s] = (node, profile, dict(zip(node.documents, site_docs[s])))
    print(f"sites built ({time.perf_counter() - t0:.0f}s)", flush=True)

    cache = TableCache()
    for s in sites:
        cache.put(s, fed[s][0].psi.blind_table())
    offline_bytes = {s: cache.tables[s].size_bytes() * 4 // 3 for s in sites}
    clusters = [NodeClusters(s, list(range(len(fed[s][1].cluster_centroids))), np.asarray(fed[s][1].cluster_centroids),
                             ["public"] * len(fed[s][1].cluster_centroids)) for s in sites]
    print(f"FedSafeRAG one-time tables: {sum(offline_bytes.values()) / 1e6:.1f} MB for {len(sites)} sites, "
          f"{sum(len(c.ids) for c in clusters)} clusters", flush=True)

    # Each question embedded on its own, timed: the device's first step in
    # every retrieval condition.
    qv, embed_ms = [], []
    for x in questions:
        t = time.perf_counter()
        v = embedder.inner.embed([x["question"]])[0]
        embed_ms.append((time.perf_counter() - t) * 1000)
        qv.append(v / max(np.linalg.norm(v), 1e-12))
    bw = args.mbps * 1e6 / 8 / 1000                       # bytes per ms

    def latency(device_ms, per_site):                    # per_site: [(site ms, bytes up, bytes down)]
        if not per_site:
            return device_ms
        return device_ms + max(args.rtt_ms + ms + (up + down) / bw for ms, up, down in per_site)

    def text_sites(chosen, i):
        """Question text to `chosen`; each searches its raw index (top-8);
        the coordinator keeps the global best 8."""
        q, question = qv[i], questions[i]["question"]
        hits, per_site = [], []
        for s in chosen:
            node, did = raw[s]
            t = time.perf_counter()
            got = node.retrieve(q, top_n=CONTEXT)
            ms = (time.perf_counter() - t) * 1000
            hits += [(did[p.document], p.document, p.score) for p in got]
            per_site.append((ms, len(question.encode("utf-8")), sum(len(p.document.encode("utf-8")) for p in got)))
        t = time.perf_counter()
        hits.sort(key=lambda h: -h[2])
        dev = (time.perf_counter() - t) * 1000
        return [(h[0], h[1]) for h in hits[:CONTEXT]], per_site, dev, len(hits)

    def run(cond, i):
        """-> passages [(doc id, text)], contacted, question text sent, records
        released, per-site [(ms, up, down)], device ms (after embedding)."""
        q = qv[i]
        if cond == "closed_book":
            return [], [], False, 0, [], 0.0
        if cond == "centralized":
            t = time.perf_counter()
            top = np.argsort(-(vecs @ q))[:CONTEXT]
            ms = (time.perf_counter() - t) * 1000
            out = [(ids[j], corpus[ids[j]]) for j in top]
            down = sum(len(x[1].encode("utf-8")) for x in out)
            return out, ["central_server"], True, CONTEXT, [(ms, len(questions[i]["question"].encode("utf-8")), down)], 0.0
        if cond == "broadcast":
            out, per_site, dev, released = text_sites(sites, i)
            return out, list(sites), True, released, per_site, dev
        if cond == "selective":
            t = time.perf_counter()
            score = {s: float(np.max(np.asarray(fed[s][1].cluster_centroids) @ q)) for s in sites}
            chosen = sorted(sites, key=lambda s: -score[s])[:args.selective_k]
            pick_ms = (time.perf_counter() - t) * 1000
            out, per_site, dev, released = text_sites(chosen, i)
            return out, chosen, True, released, per_site, dev + pick_ms
        probes = int(cond.split("_P")[1])
        t = time.perf_counter()
        plan = plan_probes(q, clusters, probes)
        dev = (time.perf_counter() - t) * 1000
        pool, per_site = [], []
        for s in sites:
            node = fed[s][0]
            t = time.perf_counter()
            evaluated = node.psi.evaluate_for(plan.points[s], ["public"])
            per_site.append(((time.perf_counter() - t) * 1000, probes * 64 + 64, probes * 64 + 64))
            t = time.perf_counter()
            opened = unlock(plan, s, evaluated, cache)
            pool += [p for cid in opened for p in opened[cid]]
            dev += (time.perf_counter() - t) * 1000
        t = time.perf_counter()
        ranked = rerank_passages(q, pool, top_n=CONTEXT)
        dev += (time.perf_counter() - t) * 1000
        did = {d: x for s in sites for d, x in fed[s][2].items()}
        return [(did.get(d, "?"), d) for d, _ in ranked], list(sites), False, len(pool), per_site, dev

    conditions = ["closed_book", "centralized", "broadcast", "selective", *[f"fedsafe_P{p}" for p in args.probes]]
    generate = set(conditions if args.generate is None else args.generate)
    generator = None
    if generate:
        from generation.ollama_generator import OllamaGenerator
        generator = OllamaGenerator(model=args.model, timeout=600.0)

    run_id = args.run_id or f"{time.strftime('%Y%m%d-%H%M%S')}_{args.topology}"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    per_q_path = RESULTS_DIR / f"cfedrag_style_{run_id}_per_question.jsonl"
    done = set()
    rows: list[dict] = []
    if per_q_path.exists():
        for line in per_q_path.read_text().splitlines():
            r = json.loads(line)
            rows.append(r)
            done.add((r["condition"], r["subset"], r["qid"]))
    answers: dict[tuple, dict] = {(r["qid"], tuple(r["passage_ids"])): r for r in rows if r.get("generated")}
    print(f"run {run_id}: {len(done)} rows already written; generating for {sorted(generate)}", flush=True)

    with open(per_q_path, "a") as out_handle:
        for cond in conditions:
            started = time.perf_counter()
            todo = [(i, x) for i, x in enumerate(questions) if (cond, x["subset"], x["qid"]) not in done]
            # Phase 1: every question's retrieval, timed while the generator is
            # idle (a pilot that interleaved the two inflated retrieval times).
            pending = []
            for i, x in todo:
                passages, contacted, text_sent, released, per_site, dev = run(cond, i)
                ret_dev = (embed_ms[i] if cond != "closed_book" else 0.0) + dev
                row = {"condition": cond, "topology": args.topology, "subset": x["subset"], "qid": x["qid"],
                       "topic": topic_of[i],
                       "passage_ids": [p[0] for p in passages],
                       "gold_at_8": float(bool(x["gold"] & {p[0] for p in passages})) if passages else 0.0,
                       "gold_in_corpus": float(bool(x["gold"] & pubmed.keys())),
                       "contacted": sorted(contacted), "sites_reading_question": len(contacted) if text_sent else 0,
                       "records_released": released,
                       "bytes_up": sum(v[1] for v in per_site), "bytes_down": sum(v[2] for v in per_site),
                       "site_ms_total": sum(v[0] for v in per_site), "site_ms_max": max((v[0] for v in per_site), default=0.0),
                       "device_ms": ret_dev, "retrieval_measured_ms": ret_dev + max((v[0] for v in per_site), default=0.0),
                       "retrieval_modelled_ms": latency(ret_dev, per_site) if cond != "closed_book" else 0.0,
                       "generated": False, "reused": False, "correct": None, "abstained": None, "generation_ms": None}
                pending.append((x, row, [p[1] for p in passages]))
            print(f"{cond}: retrieval for {len(pending)} questions ({time.perf_counter() - started:.0f}s)", flush=True)
            # Phase 2: answers.
            for n, (x, row, texts) in enumerate(pending):
                if cond in generate:
                    key = (x["qid"], tuple(row["passage_ids"]))
                    if key in answers:
                        prev = answers[key]
                        row.update(generated=True, reused=True, correct=prev["correct"], abstained=prev["abstained"],
                                   generation_ms=prev["generation_ms"], raw=prev.get("raw", ""))
                    else:
                        t = time.perf_counter()
                        raw_answer = generator.complete(prompt(x, texts), max_tokens=MAX_ANSWER_TOKENS)
                        letter = parse_letter(raw_answer, x["options"])
                        row.update(generated=True, correct=float(letter == x["answer"]), abstained=float(letter is None),
                                   generation_ms=(time.perf_counter() - t) * 1000, raw=raw_answer[:200])
                        answers[key] = row
                rows.append(row)
                out_handle.write(json.dumps(row) + "\n")
                out_handle.flush()
                if (n + 1) % 100 == 0:
                    print(f"  {cond}: {n + 1}/{len(pending)} answered ({time.perf_counter() - started:.0f}s)", flush=True)
            print(f"{cond} done ({time.perf_counter() - started:.0f}s)", flush=True)

    summary = summarise(rows, questions, args, offline_bytes, generator.model if generator else "none")
    out = RESULTS_DIR / f"cfedrag_style_{run_id}.csv"
    with open(out, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    for r in summary:
        print(json.dumps(r))
    print(f"wrote {out}")


def summarise(rows: list[dict], questions: list[dict], args, offline_bytes: dict, model: str) -> list[dict]:
    order = {(x["subset"], x["qid"]): i for i, x in enumerate(questions)}
    half = len(questions) // 2
    out = []
    for cond in dict.fromkeys(r["condition"] for r in rows):
        rs = sorted((r for r in rows if r["condition"] == cond), key=lambda r: order.get((r["subset"], r["qid"]), 0))
        gen = [r for r in rs if r["generated"]]
        acc = {s: (float(np.mean([r["correct"] for r in gen if r["subset"] == s])) if any(r["subset"] == s for r in gen)
                   else float("nan")) for s in args.subsets}
        fresh = [r["generation_ms"] for r in gen if not r["reused"]]
        topic_acc = floor = float("nan")
        if args.topology == "8hosp" and cond not in {"closed_book", "centralized"}:
            labelled = [(tuple(r["contacted"]), r["topic"]) for r in rs if r.get("topic")]
            if len(labelled) > 10:
                h = len(labelled) // 2
                att = HistoryAttacker().fit([(list(p), t) for p, t in labelled[:h]])
                topic_acc = evaluate(att, [(list(p), t) for p, t in labelled[h:]],
                                     sorted({t for _, t in labelled}))["accuracy"]
                floor = max(Counter(t for _, t in labelled[h:]).values()) / len(labelled[h:])
        out.append({
            "condition": cond, "topology": args.topology, "questions": len(rs), "answered": len(gen),
            **{f"acc_{s}": acc[s] for s in args.subsets},
            "acc_avg": float(np.nanmean(list(acc.values()))) if gen else float("nan"),
            "abstained": float(np.mean([r["abstained"] for r in gen])) if gen else float("nan"),
            "gold_at_8": float(np.mean([r["gold_at_8"] for r in rs])),
            "sites_reading_question": float(np.mean([r["sites_reading_question"] for r in rs])),
            "topic_leakage": topic_acc, "topic_floor": floor,
            "records_released": float(np.mean([r["records_released"] for r in rs])),
            "kb_per_question": float(np.mean([r["bytes_up"] + r["bytes_down"] for r in rs])) / 1e3,
            "site_cpu_ms": float(np.mean([r["site_ms_total"] for r in rs])),
            "retrieval_measured_ms_median": float(np.median([r["retrieval_measured_ms"] for r in rs])),
            "retrieval_modelled_ms_median": float(np.median([r["retrieval_modelled_ms"] for r in rs])),
            "retrieval_modelled_ms_p95": float(np.percentile([r["retrieval_modelled_ms"] for r in rs], 95)),
            "generation_ms_median": float(np.median(fresh)) if fresh else float("nan"),
            "generation_ms_p95": float(np.percentile(fresh, 95)) if fresh else float("nan"),
            "reused_answers": sum(1 for r in gen if r["reused"]),
            "one_time_table_mb": sum(offline_bytes.values()) / 1e6 if cond.startswith("fedsafe") else 0.0,
            "rtt_ms": args.rtt_ms, "mbps": args.mbps, "model": model,
        })
    return out


if __name__ == "__main__":
    main()
