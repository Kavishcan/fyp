"""Published federated-RAG systems vs blind unlock: quality, privacy, COST (docs/53).

Baselines (backend/baselines/external_fedrag.py has the provenance):
- flower_fedrag        Flower's fedrag example: the question goes to EVERY
                       hospital; each embeds it with all-MiniLM-L6-v2,
                       searches FAISS IndexIVFFlat (L2, nlist sqrt(N), FAISS
                       default nprobe 1), returns its top-10; server RRF merge.
- flower_fedrag_bge    the same with bge-base, to separate the embedder from
                       the design.
- hyfedrag_style       docs/46: broadcast text, each hospital embeds (bge) and
                       returns an exact top-10, server fuses by score.
- ragroute             RAGRoute: the coordinator embeds the question, a trained
                       MLP picks hospitals (p > 0.5), each picked hospital
                       receives the question text AND its embedding (as in
                       ragroute/http_server.py) and returns an exact top-50;
                       ranked by score (the 2 GB cross-encoder is replaced —
                       stated).  *_hybrid: dense + pool BM25 (docs/48).
- ours_blind_P*        blind unlock (docs/47): P real-or-dummy points to every
                       hospital; table download offline.

Protocol: the RAGRoute router is trained on 30% of the queries, validated on
10%; EVERY configuration is scored on the remaining 60% (test). Labels for
RAGRoute: a hospital is relevant if it holds one of the centralized top-15.

Cost, per question:
- hospitals contacted, and hospitals that do work on the question;
- hospital compute: measured on this machine. A hospital that receives text
  must embed it: the per-question embedding time is measured once per model
  with no cache and charged to every hospital that embeds that question (same
  hardware assumed); search / OPRF evaluation is measured per contact;
- device/coordinator compute (embedding, routing, unlock, ranking);
- bytes each way (JSON payload sizes; blind: hex points as in the harness);
- modelled latency: device + max over contacts (RTT + hospital ms + bytes /
  bandwidth); contacts in parallel; `--rtt-ms`, `--mbps` (a model, stated).
Privacy: hospitals that receive the question; topic inference from the
contact pattern (attacker trained on the first half of the test queries).

Run: python -m eval.run_external_baselines --queries 1000
"""
from __future__ import annotations

import argparse
import csv
import os
import json
import time
from collections import Counter

import numpy as np

os.environ.setdefault("OMP_NUM_THREADS", "1")   # FAISS + torch each ship OpenMP; two pools segfault on macOS

from attacks.a2_topic_inference import HistoryAttacker, evaluate
from baselines.external_fedrag import FlowerClientIndex, RAGRouteRouter, flower_merge_documents
from eval.embed_cache import CachedEmbedder
from eval.run_hyfedrag_compare import build_nodes, load, mrr, ndcg_at, p_at
from eval.sweep import REPO_ROOT, RESULTS_DIR
from nodes.embedding import SentenceTransformerEmbedder
from privacy.blind_unlock import NodeClusters, TableCache, plan_probes, unlock
from privacy.cluster_index import kmeans_unit, rerank_passages
from privacy.deidentify import presidio_backend
from router.hybrid_rerank import DEFAULT_WEIGHT, hybrid_scores, tokenize

BGE = "BAAI/bge-base-en-v1.5"
MINILM = "sentence-transformers/all-MiniLM-L6-v2"


def unit(x: np.ndarray) -> np.ndarray:
    return x / np.maximum(np.linalg.norm(x, axis=-1, keepdims=True), 1e-12)


def timed_embed_ms(model_name: str, texts: list[str]) -> list[float]:
    """Uncached single-question embedding time — what a hospital pays."""
    model = SentenceTransformerEmbedder(model_name)
    model.embed(texts[:3])                                    # warm-up
    out = []
    for t in texts:
        t0 = time.perf_counter()
        model.embed([t])
        out.append((time.perf_counter() - t0) * 1000)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--queries", type=int, default=1000)
    parser.add_argument("--corpus", type=int, default=5000)
    parser.add_argument("--clients", type=int, default=8)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--partition", choices=["kmeans", "dirichlet", "random"], default="kmeans")
    parser.add_argument("--dirichlet-alpha", type=float, default=0.5)
    parser.add_argument("--rtt-ms", type=float, default=40.0)
    parser.add_argument("--mbps", type=float, default=100.0)
    parser.add_argument("--only", nargs="*", default=None)
    args = parser.parse_args()

    t0 = time.perf_counter()
    corpus, queries = load(args.queries, args.corpus, args.seed)
    uids = list(corpus)
    bge = CachedEmbedder(SentenceTransformerEmbedder(BGE))
    vecs = unit(bge.embed([corpus[u] for u in uids]))
    qv = unit(bge.embed([t for _, t, _ in queries]))

    # Hospitals: the docs/46 / docs/50 split, same seed.
    _, assign = kmeans_unit(vecs, args.clients, args.seed)
    if args.partition != "kmeans":
        prng = np.random.default_rng(args.seed + 1000)
        topic_of = assign.copy()
        assign = np.empty_like(topic_of)
        for t in np.unique(topic_of):
            idx = np.where(topic_of == t)[0]
            props = (prng.dirichlet([args.dirichlet_alpha] * args.clients) if args.partition == "dirichlet"
                     else np.full(args.clients, 1.0 / args.clients))
            assign[idx] = prng.choice(args.clients, size=len(idx), p=props)
    client_of = {u: f"hospital_{int(a)}" for u, a in zip(uids, assign.tolist())}
    client_docs: dict[str, list[tuple[str, str]]] = {}
    for u in uids:
        client_docs.setdefault(client_of[u], []).append((u, corpus[u]))
    clients = sorted(client_docs)
    topic = [Counter(client_of[u] for u in rel).most_common(1)[0][0] for *_, rel in queries]
    print(f"{len(corpus)} patients, {len(queries)} queries, hospitals "
          f"{dict(sorted(Counter(client_of.values()).items()))} ({time.perf_counter() - t0:.0f}s)", flush=True)

    # Split for RAGRoute (by query); every configuration is scored on test.
    order = np.random.default_rng(args.seed).permutation(len(queries))
    n_tr, n_va = int(0.3 * len(queries)), int(0.1 * len(queries))
    train, val, test = order[:n_tr], order[n_tr:n_tr + n_va], order[n_tr + n_va:]

    # Per-hospital raw data (baselines run on raw indexes, as in docs/46).
    h_uids = {c: [u for u, _ in client_docs[c]] for c in clients}
    h_text = {c: [t for _, t in client_docs[c]] for c in clients}
    pos = {u: i for i, u in enumerate(uids)}
    h_vecs = {c: vecs[[pos[u] for u in h_uids[c]]] for c in clients}
    h_counts = {c: [Counter(tokenize(t)) for t in h_text[c]] for c in clients}

    # Flower clients: MiniLM (the example's model) and bge, FAISS IVF L2.
    minilm = CachedEmbedder(SentenceTransformerEmbedder(MINILM))
    flower_idx = {
        "minilm": {c: FlowerClientIndex(h_uids[c], unit(minilm.embed(h_text[c])).astype("float32")) for c in clients},
        "bge": {c: FlowerClientIndex(h_uids[c], h_vecs[c].astype("float32")) for c in clients},
    }
    q_minilm = unit(minilm.embed([t for _, t, _ in queries]))
    print(f"flower indexes ready ({time.perf_counter() - t0:.0f}s)", flush=True)

    # What one question costs to embed, uncached, on this machine.
    test_texts = [queries[i][1] for i in test]
    embed_ms = {"bge": dict(zip(test.tolist(), timed_embed_ms(BGE, test_texts))),
                "minilm": dict(zip(test.tolist(), timed_embed_ms(MINILM, test_texts)))}
    print(f"question embedding: bge {np.mean(list(embed_ms['bge'].values())):.1f} ms, "
          f"MiniLM {np.mean(list(embed_ms['minilm'].values())):.1f} ms ({time.perf_counter() - t0:.0f}s)", flush=True)

    # RAGRoute router: labels from the centralized top-15.
    def labels(i):
        top = np.argsort(-(vecs @ qv[i]))[:15]
        return {client_of[uids[j]] for j in top}
    centroids = {c: unit(h_vecs[c].mean(0)) for c in clients}
    t_fit = time.perf_counter()
    router = RAGRouteRouter(clients, centroids, seed=args.seed).fit(
        [qv[i] for i in train], [labels(i) for i in train], [qv[i] for i in val], [labels(i) for i in val])
    print(f"RAGRoute router: val AUC {router.val_auc:.3f}, trained in {time.perf_counter() - t_fit:.0f}s; "
          f"oracle hospitals per test query {np.mean([len(labels(i)) for i in test]):.2f}", flush=True)

    # Blind unlock: our de-identified nodes, offline tables.
    our_nodes = build_nodes(client_docs, bge, args.seed, presidio_backend(), deidentify=True)
    cache = TableCache()
    for c in clients:
        cache.put(c, our_nodes[c][0].psi.blind_table())
    offline_bytes = sum(cache.tables[c].size_bytes() * 4 // 3 for c in clients)
    blind_clusters = [NodeClusters(c, list(range(len(our_nodes[c][1].cluster_centroids))),
                                   np.asarray(our_nodes[c][1].cluster_centroids),
                                   ["public"] * len(our_nodes[c][1].cluster_centroids)) for c in clients]
    uid_by_doc = {d: u for c in clients for d, u in our_nodes[c][2].items()}
    print(f"blind tables {offline_bytes / 1e6:.1f} MB offline ({time.perf_counter() - t0:.0f}s)", flush=True)

    def hybrid(question, q, docs, dvecs, k, counts=None):
        s = hybrid_scores(question, q, docs, np.asarray(dvecs), DEFAULT_WEIGHT, counts=counts)
        return list(np.argsort(-s)[:k])

    def exact_top(c, q, k):
        s = h_vecs[c] @ q
        top = np.argsort(-s)[:k]
        return [(h_uids[c][j], float(s[j])) for j in top]

    def reply_bytes(c_uids_scores) -> int:
        return len(json.dumps({"docs": [corpus[u] for u, _ in c_uids_scores], "ids": [u for u, _ in c_uids_scores],
                               "scores": [s for _, s in c_uids_scores]}).encode("utf-8"))

    # Each run returns: ranked uids, {hospital: (hospital_ms, bytes_up, bytes_down, works_on_question)},
    # device_ms, question text reached hospitals, records disclosed.
    def run(name, i):
        question, q = queries[i][1], qv[i]
        qbytes = len(json.dumps({"query": question}).encode("utf-8"))
        if name.startswith("centralized"):
            if name.endswith("_hybrid"):
                order_ = hybrid(question, q, [corpus[u] for u in uids], vecs, 10)
                return [uids[j] for j in order_], {}, 0.0, False, 0
            return [uids[j] for j in np.argsort(-(vecs @ q))[:10]], {}, 0.0, False, 0
        if name.startswith("flower_fedrag"):
            kind = "bge" if name.startswith("flower_fedrag_bge") else "minilm"
            qq = q if kind == "bge" else q_minilm[i]
            docs, scores, per = [], [], {}
            for c in clients:
                t_s = time.perf_counter()
                hits = flower_idx[kind][c].search(qq, 10)
                search_ms = (time.perf_counter() - t_s) * 1000
                per[c] = (embed_ms[kind][i] + search_ms, qbytes, reply_bytes(hits), True)
                docs += [u for u, _ in hits]
                scores += [s for _, s in hits]
            t_d = time.perf_counter()
            ranked = flower_merge_documents(docs, scores, 10, k_rrf=60)
            return ranked, per, (time.perf_counter() - t_d) * 1000, True, len(docs)
        if name.startswith("hyfedrag_style"):
            pool, per = [], {}
            for c in clients:
                t_s = time.perf_counter()
                if name.endswith("_hybrid"):
                    idx = hybrid(question, q, h_text[c], h_vecs[c], 10, counts=h_counts[c])
                    hits = [(h_uids[c][j], float(h_vecs[c][j] @ q)) for j in idx]
                else:
                    hits = exact_top(c, q, 10)
                per[c] = (embed_ms["bge"][i] + (time.perf_counter() - t_s) * 1000, qbytes, reply_bytes(hits), True)
                pool += hits
            t_d = time.perf_counter()
            if name.endswith("_hybrid"):
                idx = hybrid(question, q, [corpus[u] for u, _ in pool], [vecs[pos[u]] for u, _ in pool], 10)
                ranked = [pool[j][0] for j in idx]
            else:
                ranked = [u for u, _ in sorted(pool, key=lambda x: -x[1])[:10]]
            return ranked, per, (time.perf_counter() - t_d) * 1000, True, len(pool)
        if name.startswith("ragroute"):
            t_d = time.perf_counter()
            chosen = router.route(q)
            device_ms = embed_ms["bge"][i] + (time.perf_counter() - t_d) * 1000
            up = len(json.dumps({"id": 0, "query": question, "embedding": [float(x) for x in q.astype(np.float32)]})
                     .encode("utf-8"))
            pool, per = [], {}
            for c in chosen:
                t_s = time.perf_counter()
                hits = exact_top(c, q, 50)
                per[c] = ((time.perf_counter() - t_s) * 1000, up, reply_bytes(hits), True)
                pool += hits
            t_d = time.perf_counter()
            if not pool:
                ranked = []
            elif name.endswith("_hybrid"):
                idx = hybrid(question, q, [corpus[u] for u, _ in pool], [vecs[pos[u]] for u, _ in pool], 10)
                ranked = [pool[j][0] for j in idx]
            else:
                ranked = [u for u, _ in sorted(pool, key=lambda x: -x[1])[:10]]
            return ranked, per, device_ms + (time.perf_counter() - t_d) * 1000, True, len(pool)
        # blind unlock
        P = int(name.split("_P")[1].split("_")[0])
        t_d = time.perf_counter()
        plan = plan_probes(q, blind_clusters, P)
        device_ms = embed_ms["bge"][i] + (time.perf_counter() - t_d) * 1000
        pool, per = [], {}
        for c in clients:
            t_s = time.perf_counter()
            evaluated = our_nodes[c][0].psi.evaluate_for(plan.points[c], ["public"])
            per[c] = ((time.perf_counter() - t_s) * 1000, P * 64 + 64, P * 64 + 64, False)
            t_d = time.perf_counter()
            opened = unlock(plan, c, evaluated, cache)
            pool += [p for cid in opened for p in opened[cid]]
            device_ms += (time.perf_counter() - t_d) * 1000
        t_d = time.perf_counter()
        if name.endswith("_hybrid") and pool:
            idx = hybrid(question, q, [p["document"] for p in pool], [p["embedding"] for p in pool], 10)
            ranked = [pool[j]["document"] for j in idx]
        else:
            ranked = [d for d, _ in rerank_passages(q, pool, top_n=10)]
        device_ms += (time.perf_counter() - t_d) * 1000
        return [uid_by_doc[d] for d in ranked], per, device_ms, False, len(pool)

    configs = ["centralized", "centralized_hybrid", "flower_fedrag", "flower_fedrag_bge", "hyfedrag_style",
               "hyfedrag_style_hybrid", "ragroute", "ragroute_hybrid", "ours_blind_P8", "ours_blind_P8_hybrid",
               "ours_blind_P24_hybrid"]
    bw = args.mbps * 1e6 / 8 / 1000                                  # bytes per ms
    rows, per_query = [], {}
    half = len(test) // 2
    for name in [c for c in configs if args.only is None or c in args.only]:
        rec = {k: [] for k in ("mrr", "p10", "ndcg", "contacts", "working", "exposed", "hosp_total", "hosp_max",
                               "device", "up", "down", "latency", "records", "zero")}
        patterns = []
        for i in test.tolist():
            ranked, per, device_ms, text_sent, records = run(name, i)
            rel = queries[i][2]
            rec["mrr"].append(mrr(ranked, rel)); rec["p10"].append(p_at(ranked, rel)); rec["ndcg"].append(ndcg_at(ranked, rel))
            rec["contacts"].append(len(per)); rec["working"].append(sum(1 for v in per.values() if v[3]))
            rec["exposed"].append(1.0 if text_sent and per else 0.0)
            hosp = [v[0] for v in per.values()]
            rec["hosp_total"].append(sum(hosp)); rec["hosp_max"].append(max(hosp, default=0.0))
            rec["device"].append(device_ms)
            rec["up"].append(sum(v[1] for v in per.values())); rec["down"].append(sum(v[2] for v in per.values()))
            rec["latency"].append(device_ms + max((args.rtt_ms + v[0] + (v[1] + v[2]) / bw for v in per.values()),
                                                  default=0.0))
            rec["records"].append(records); rec["zero"].append(1.0 if not per and not name.startswith("central") else 0.0)
            patterns.append(sorted(per))
        per_query[name] = [float(x) for x in rec["mrr"]]
        topic_acc = float("nan")
        test_topic = [topic[i] for i in test.tolist()]
        if not name.startswith("central"):
            att = HistoryAttacker().fit(list(zip(patterns[:half], test_topic[:half])))
            topic_acc = evaluate(att, list(zip(patterns[half:], test_topic[half:])), sorted(set(topic)))["accuracy"]
        m = {k: float(np.mean(v)) for k, v in rec.items()}
        rows.append({"configuration": name, "test_queries": len(test), "mrr": m["mrr"], "p@10": m["p10"],
                     "ndcg@10": m["ndcg"], "hospitals_contacted": m["contacts"],
                     "hospitals_processing_question": m["working"], "query_text_to_hospitals": m["exposed"],
                     "topic_inference": topic_acc,
                     "topic_majority_floor": max(Counter(test_topic[half:]).values()) / len(test_topic[half:]),
                     "hospital_cpu_ms_total": m["hosp_total"], "slowest_hospital_ms": m["hosp_max"],
                     "device_ms": m["device"], "bytes_up": m["up"], "bytes_down": m["down"],
                     "modelled_latency_ms": m["latency"], "modelled_latency_p95_ms": float(np.percentile(rec["latency"], 95)),
                     "records_to_device": m["records"], "no_hospital_selected": m["zero"],
                     "offline_bytes_total": float(offline_bytes) if name.startswith("ours_blind") else 0.0})
        r = rows[-1]
        print(f"  {name:<22} MRR {r['mrr']:.3f} nDCG {r['ndcg@10']:.3f} | contacts {r['hospitals_contacted']:.2f} "
              f"(see q {r['hospitals_processing_question']:.2f}) q-text {r['query_text_to_hospitals']:.2f} "
              f"topic {r['topic_inference']:.3f}/{r['topic_majority_floor']:.3f} | hospital ms total "
              f"{r['hospital_cpu_ms_total']:.1f} max {r['slowest_hospital_ms']:.1f} | device {r['device_ms']:.1f} ms "
              f"| up {r['bytes_up'] / 1e3:.1f} KB down {r['bytes_down'] / 1e3:.1f} KB | latency {r['modelled_latency_ms']:.0f} ms "
              f"| records {r['records_to_device']:.0f} | none {r['no_hospital_selected']:.3f}", flush=True)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / f"external_baselines_{args.partition}_c{args.clients}_{time.strftime('%Y%m%d-%H%M%S')}.csv"
    out.with_suffix(".perquery.json").write_text(json.dumps({
        "partition": args.partition, "clients": args.clients, "seed": args.seed, "rtt_ms": args.rtt_ms,
        "mbps": args.mbps, "router_val_auc": router.val_auc, "test_query_ids": [queries[i][0] for i in test.tolist()],
        "mrr": per_query}))
    with out.open("w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out} ({time.perf_counter() - t0:.0f}s)")


if __name__ == "__main__":
    main()
