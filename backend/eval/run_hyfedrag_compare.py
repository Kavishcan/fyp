"""HyFedRAG-style design vs this project on PMC-Patients (docs/46).

HyFedRAG (Qian et al., arXiv 2509.06444) publishes no code, so its
PRIVACY-RELEVANT design is reimplemented here as one more configuration in
this project's harness, and both are measured on the same data, with the
same metrics and the same attacks. This is a reimplementation of the
described design, not HyFedRAG's system; its heterogeneous-data handling
(SQL, knowledge graphs) and caching are not reproduced.

Data: PMC-Patients (Zhao et al.; the dataset HyFedRAG evaluates on).
Task: patient-to-patient retrieval — the query is a patient summary; the
relevant documents are its annotated similar patients. Only CROSS-article
similar patients count: patients from the query's own case report (score 2
in the dataset) are trivially similar, so they are removed from the corpus.
Metrics HyFedRAG reports: MRR, P@10, nDCG@10 (graded where available).

Federation: the corpus is split into `--clients` simulated hospitals by
spherical k-means on bge-base embeddings (topic-coherent, uneven sizes —
the docs/40 method). A query's topic label is the client holding most of
its relevant patients.

Configurations:
- centralized       one index over everything — the reference HyFedRAG
                    compares against.
- hyfedrag_style    every client is contacted with the query text; each
                    retrieves its top-10 locally; the server fuses by score.
                    Ranking runs over the raw local index (HyFedRAG's edge
                    retriever sees raw data); its edge de-identification —
                    Presidio with stock settings (PERSON + LOCATION) — is
                    measured separately as damage to the delivered text.
- cosine_router     a normal router: top-4 clients by profile cosine, query
                    text sent, fused top-10.
- ours_psi_cells    this project: local routing, whole fixed anonymity cell
                    of the top client (cells of 4), PSI dispatch (blinded
                    cluster ids, nprobe 2), rerank across nodes, top-10;
                    node de-identification: rules + full-name NER (docs/44).
- ours_psi_top4     PSI dispatch to the cosine top-4, no cells — separates
                    the retrieval cost of PSI bucketing from that of cells.
- *_hybrid          the same configuration with device/server ranking by
                    dense cosine + pool BM25 (router/hybrid_rerank.py,
                    docs/48); HyFedRAG-style hybrid also ranks each
                    hospital's local top-10 by hybrid (a hospital sees the
                    question, so it may). One weight for every configuration.
- ours_blind_P*     blind unlock (docs/47): every hospital's encrypted table
                    downloaded once (offline, reported separately); per
                    question the device unlocks the P best clusters across
                    ALL hospitals and sends exactly P points — real or dummy —
                    to every hospital.

Measured per configuration: retrieval (MRR, P@10, nDCG@10), contacts per
query, whether contacted hospitals receive the query text, topic inference
from the contact pattern (learned observer, docs/39), bytes sent per query,
and de-identification damage to clean clinical text (share of documents
altered and the retrieval change it causes).

PMC-Patients case reports are already de-identified by their journals, so
no real identifiers are present; the de-identification rows measure false
positives on realistic clinical prose, not PII recall (that is docs/44).

Run: python -m eval.run_hyfedrag_compare
"""
from __future__ import annotations

import argparse
import ast
import csv
import json
import math
import random
import time
from collections import Counter

import numpy as np

from attacks.a2_topic_inference import HistoryAttacker, evaluate
from eval.embed_cache import CachedEmbedder
from eval.sweep import REPO_ROOT, RESULTS_DIR, SentenceTransformerEmbedder
from nodes.simulator import build_simulated_source
from privacy.cluster_index import assign_clusters, kmeans_unit, rerank_passages
from privacy.deidentify import presidio_backend
from privacy.blind_unlock import NodeClusters, TableCache, plan_probes, unlock
from privacy.psi import PSIClient
from router.hybrid_rerank import DEFAULT_WEIGHT, hybrid_scores, tokenize
from router.anonymity import build_cells, cell_cover

CSV_PATH = REPO_ROOT / "backend" / "vendor" / "pmc_patients" / "PMC-Patients.csv"


def load(n_queries: int, corpus_size: int, seed: int):
    import pandas as pd

    df = pd.read_csv(CSV_PATH, usecols=["patient_uid", "PMID", "patient", "similar_patients"])
    df["PMID"] = df["PMID"].astype(str)
    text = dict(zip(df["patient_uid"], df["patient"]))
    pmid = dict(zip(df["patient_uid"], df["PMID"]))
    rng = random.Random(seed)
    candidates = []
    for uid, sim in zip(df["patient_uid"], df["similar_patients"]):
        rel = ast.literal_eval(sim) if isinstance(sim, str) else {}
        cross = {u: int(s) for u, s in rel.items() if u in text and pmid.get(u) != pmid[uid]}
        if cross:
            candidates.append((uid, cross))
    rng.shuffle(candidates)
    queries = candidates[:n_queries]
    query_pmids = {pmid[q] for q, _ in queries}
    relevant_pool = {u for _, rel in queries for u in rel if pmid[u] not in query_pmids}
    filler = [u for u in df["patient_uid"] if pmid[u] not in query_pmids and u not in relevant_pool]
    rng.shuffle(filler)
    corpus_ids = sorted(relevant_pool) + filler[: max(0, corpus_size - len(relevant_pool))]
    corpus = {u: text[u] for u in corpus_ids}
    q = [(qid, text[qid], {u: s for u, s in rel.items() if u in corpus}) for qid, rel in queries]
    q = [x for x in q if x[2]]
    return corpus, q


# --- metrics ------------------------------------------------------------------


def mrr(ranked: list[str], rel: dict[str, int]) -> float:
    for i, d in enumerate(ranked):
        if d in rel:
            return 1.0 / (i + 1)
    return 0.0


def p_at(ranked: list[str], rel: dict[str, int], k: int = 10) -> float:
    return sum(1 for d in ranked[:k] if d in rel) / k


def ndcg_at(ranked: list[str], rel: dict[str, int], k: int = 10) -> float:
    dcg = sum(rel.get(d, 0) / math.log2(i + 2) for i, d in enumerate(ranked[:k]))
    ideal = sorted(rel.values(), reverse=True)[:k]
    idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal))
    return dcg / idcg if idcg else 0.0


# --- nodes ----------------------------------------------------------------------


def build_nodes(client_docs: dict[str, list[tuple[str, str]]], embedder, seed: int, deid_backend, deidentify: bool):
    """Returns node_id -> (node, profile, text->uid map)."""
    out = {}
    for i, (cid, docs) in enumerate(client_docs.items()):
        uids, texts = zip(*docs)
        node, profile = build_simulated_source(cid, list(texts), embedder, k=3, sigma=0.0,
                                               rng=np.random.default_rng(seed + i), deidentify=deidentify,
                                               deid_backend=deid_backend)
        out[cid] = (node, profile, dict(zip(node.documents, uids)))
    return out


def dense_top(node, uid_of, qvec, k=10) -> list[tuple[str, float]]:
    return [(uid_of[p.document], p.score) for p in node.retrieve(qvec, top_n=k)]


def psi_top(node, profile, uid_of, qvec, nprobe=2) -> list[dict]:
    """One in-process PSI contact: assign, blind, OPRF, open (real crypto)."""
    wanted = assign_clusters(qvec, profile.cluster_centroids, nprobe=nprobe)
    q = PSIClient.blind(wanted)
    opened = PSIClient.open_matches_multi(q, node.psi.evaluate_for(q.blinded, ["public"]), node.source_id,
                                          node.psi.envelopes_for(None))
    return [p for cid in wanted for p in opened.get(cid, [])]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--queries", type=int, default=300)
    parser.add_argument("--corpus", type=int, default=5000)
    parser.add_argument("--clients", type=int, default=8)
    parser.add_argument("--router-k", type=int, default=4)
    parser.add_argument("--cell-size", type=int, default=4)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--skip-stock-deid", action="store_true",
                        help="skip the stock-Presidio node build (only used for the de-id damage row)")
    parser.add_argument("--embedder-model", default="BAAI/bge-base-en-v1.5")
    parser.add_argument("--hybrid-weight", type=float, default=DEFAULT_WEIGHT)
    parser.add_argument("--partition", choices=["kmeans", "dirichlet", "random"], default="kmeans",
                        help="how patients are split into hospitals: k-means in the routing embedding (docs/46), "
                             "Dirichlet non-IID over k-means topics, or uniform random (robustness, docs/50)")
    parser.add_argument("--dirichlet-alpha", type=float, default=0.5)
    parser.add_argument("--only", nargs="*", default=None,
                        help="run only these configurations (e.g. ours_blind_P8); default all")
    args = parser.parse_args()

    t0 = time.perf_counter()
    corpus, queries = load(args.queries, args.corpus, args.seed)
    print(f"PMC-Patients: {len(corpus)} corpus patients, {len(queries)} queries with cross-article similar patients "
          f"(mean {np.mean([len(r) for *_, r in queries]):.2f} relevant) in {time.perf_counter() - t0:.0f}s", flush=True)
    embedder = CachedEmbedder(SentenceTransformerEmbedder(args.embedder_model))

    uids = list(corpus)
    vecs = embedder.embed([corpus[u] for u in uids])
    vecs = vecs / np.maximum(np.linalg.norm(vecs, axis=1, keepdims=True), 1e-12)
    _, assign = kmeans_unit(vecs, args.clients, args.seed)
    if args.partition != "kmeans":
        # Robustness (docs/50): k-means in the routing embedding makes both
        # routing and topic inference easy. "dirichlet": each k-means topic's
        # patients are spread over hospitals with proportions ~ Dir(alpha)
        # (the usual non-IID federated split); "random": uniform (IID).
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
    print(f"clients: {dict(sorted(Counter(client_of.values()).items()))} ({time.perf_counter() - t0:.0f}s)", flush=True)

    qv = embedder.embed([t for _, t, _ in queries])
    qv = qv / np.maximum(np.linalg.norm(qv, axis=1, keepdims=True), 1e-12)
    topic = [Counter(client_of[u] for u in rel).most_common(1)[0][0] for *_, rel in queries]

    # Centralized reference: exact dense retrieval over everything.
    def centralized(i, hybrid=False):
        if hybrid:
            order, _ = hybrid_top(queries[i][1], qv[i], [corpus[u] for u in uids], vecs, 10, counts=corpus_counts)
            return [uids[j] for j in order]
        scores = vecs @ qv[i]
        return [uids[j] for j in np.argsort(-scores)[:10]]

    ner = presidio_backend()
    stock = None if args.skip_stock_deid else presidio_backend(entities=("PERSON", "LOCATION"), full_names_only=False)
    print("building nodes: no de-id / stock Presidio (HyFedRAG-style) / rules + full-name NER (ours)", flush=True)
    raw_nodes = build_nodes(client_docs, embedder, args.seed, None, deidentify=False)
    hy_nodes = None if stock is None else build_nodes(client_docs, embedder, args.seed, stock, deidentify=True)
    our_nodes = build_nodes(client_docs, embedder, args.seed, ner, deidentify=True)
    print(f"nodes ready ({time.perf_counter() - t0:.0f}s)", flush=True)

    clients = sorted(client_docs)
    from baselines.cosine_router import CosineRouter

    router = CosineRouter(aggregation="max")
    router.register_sources([our_nodes[c][1] for c in clients])
    cells = build_cells(clients, {c: c for c in clients}, args.cell_size)

    cells2 = build_cells(clients, {c: c for c in clients}, 2)
    psi_table_bytes = {c: 2 * sum(len(v) for v in our_nodes[c][0].psi.table.values()) for c in clients}  # hex on the wire

    def rank_hospitals(q, k, fine: bool) -> list[str]:
        """coarse: the profile's few routing centroids (router/v2 default).
        fine: each hospital's best-matching PUBLIC cluster centroid — finer
        information the device already holds for PSI; no new disclosure."""
        if not fine:
            return list(router.rank(q, top_k=k).ranked_source_ids)
        scores = {c: float(np.max(np.asarray(our_nodes[c][1].cluster_centroids) @ q)) for c in clients}
        return sorted(scores, key=lambda c: -scores[c])[:k]

    # name -> (selection, fine routing, dispatch, nprobe)
    CONFIGS = {
        "centralized": ("central", False, "dense", 0),
        "hyfedrag_style": ("all", False, "text", 0),
        "cosine_router": ("top4", False, "text", 0),
        "cosine_router_fine": ("top4", True, "text", 0),
        "ours_psi_top4": ("top4", False, "psi", 2),
        "ours_psi_cells": ("cell4", False, "psi", 2),
        "ours_psi_cells_fine": ("cell4", True, "psi", 2),
        "ours_psi_cells_fine_np3": ("cell4", True, "psi", 3),
        "ours_psi_cells_fine_np4": ("cell4", True, "psi", 4),
        "ours_psi_cells2x2_fine_np3": ("cell2x2", True, "psi", 3),
        "ours_psi_broadcast_np2": ("all", True, "psi", 2),
        "ours_psi_broadcast_np3": ("all", True, "psi", 3),
        "ours_blind_P4": ("all", True, "blind", 4),
        "ours_blind_P8": ("all", True, "blind", 8),
        "ours_blind_P16": ("all", True, "blind", 16),
        "ours_blind_P24": ("all", True, "blind", 24),
        # docs/48: same configurations, hybrid (dense + pool BM25) ranking
        "centralized_hybrid": ("central", False, "dense", 0),
        "hyfedrag_style_hybrid": ("all", False, "text", 0),
        "ours_psi_cells_hybrid": ("cell4", False, "psi", 2),
        "ours_blind_P8_hybrid": ("all", True, "blind", 8),
        "ours_blind_P16_hybrid": ("all", True, "blind", 16),
        "ours_blind_P24_hybrid": ("all", True, "blind", 24),
    }
    W = args.hybrid_weight
    from collections import Counter as _Counter
    corpus_counts = [_Counter(tokenize(corpus[u])) for u in uids]           # centralized index, built once
    raw_counts = {c: [_Counter(tokenize(d)) for d in raw_nodes[c][0].documents] for c in clients}   # each hospital's own index

    def hybrid_top(question, q, docs, vectors, k, counts=None):
        s_ = hybrid_scores(question, q, docs, vectors, W, counts=counts)
        return list(np.argsort(-s_)[:k]), s_

    # Blind unlock, offline step: every hospital's public table, downloaded
    # once per key epoch. Measured here once; not charged to any question.
    t_off = time.perf_counter()
    blind_cache = TableCache()
    for c in clients:
        blind_cache.put(c, our_nodes[c][0].psi.blind_table())
    offline_s = time.perf_counter() - t_off
    offline_bytes = {c: blind_cache.tables[c].size_bytes() * 4 // 3 for c in clients}   # base64 on the wire
    blind_clusters = [NodeClusters(c, list(range(len(our_nodes[c][1].cluster_centroids))),
                                   np.asarray(our_nodes[c][1].cluster_centroids),
                                   ["public"] * len(our_nodes[c][1].cluster_centroids)) for c in clients]
    uid_by_doc = {d: u for c in clients for d, u in our_nodes[c][2].items()}
    print(f"blind tables: {sum(offline_bytes.values()) / 1e6:.1f} MB for {len(clients)} hospitals "
          f"(largest {max(offline_bytes.values()) / 1e6:.1f} MB; per-query PSI ships {sum(psi_table_bytes.values()) / 1e6:.0f} MB "
          f"for all 8), built in {offline_s:.1f}s", flush=True)

    def run(name, i):
        """Returns ranked uids, contacted hospitals, bytes sent, bytes received,
        passages disclosed, whether the question text reached hospitals."""
        q = qv[i]
        question = queries[i][1]
        selection, fine, dispatch, nprobe = CONFIGS[name]
        hybrid = name.endswith("_hybrid")
        if selection == "central":
            return centralized(i, hybrid), [], 0, 0, 0, False
        if selection == "all":
            chosen = list(clients)
        elif selection == "top4":
            chosen = rank_hospitals(q, args.router_k, fine)
        elif selection == "cell4":
            chosen = cell_cover(rank_hospitals(q, 1, fine), cells, max(len(c) for c in cells))
        else:  # cell2x2: whole cells of size 2 for the top-2 hospitals
            chosen = cell_cover(rank_hospitals(q, 2, fine), cells2, 2 * max(len(c) for c in cells2))
        if dispatch == "blind":
            t_dev = time.perf_counter()
            plan = plan_probes(q, blind_clusters, nprobe)
            device_ms = (time.perf_counter() - t_dev) * 1000
            pool, node_ms = [], []
            for c in chosen:
                node = our_nodes[c][0]
                t_node = time.perf_counter()
                evaluated = node.psi.evaluate_for(plan.points[c], ["public"])    # the hospital's work
                node_ms.append((time.perf_counter() - t_node) * 1000)
                t_dev = time.perf_counter()
                opened = unlock(plan, c, evaluated, blind_cache)
                pool += [p for cid in opened for p in opened[cid]]
                device_ms += (time.perf_counter() - t_dev) * 1000
            t_dev = time.perf_counter()
            if hybrid and pool:
                order, s_ = hybrid_top(question, q, [p["document"] for p in pool],
                                       np.asarray([p["embedding"] for p in pool]), 10)
                ranked = [(pool[j]["document"], float(s_[j])) for j in order]
            else:
                ranked = rerank_passages(q, pool, top_n=10)
            device_ms += (time.perf_counter() - t_dev) * 1000
            split.append((device_ms, max(node_ms)))
            sent = len(chosen) * (nprobe * 64 + 64)                # P points (hex) to every hospital + framing
            received = len(chosen) * (nprobe * 64 + 64)            # P evaluations back; tables are cached
            return [uid_by_doc[d] for d, _ in ranked], chosen, sent, received, len(pool), False
        if dispatch == "text":
            # HyFedRAG and a normal router: the question goes to every contacted
            # hospital; each returns its local top-10 over its RAW index.
            sent = len(queries[i][1].encode("utf-8")) * len(chosen)
            received = sum(len(raw_nodes[c][0].documents[0]) for c in chosen) * 10 // 1   # ~10 passages each
            if hybrid:
                # each hospital ranks its own index by hybrid (it sees the question), the
                # server re-ranks the union by hybrid with pool statistics
                pool_docs, pool_vecs, pool_uids = [], [], []
                for c in chosen:
                    node = raw_nodes[c][0]
                    order, _ = hybrid_top(question, q, node.documents, node.document_embeddings, 10, counts=raw_counts[c])
                    for j in order:
                        pool_docs.append(node.documents[j]); pool_vecs.append(node.document_embeddings[j])
                        pool_uids.append(raw_nodes[c][2][node.documents[j]])
                order, _ = hybrid_top(question, q, pool_docs, np.asarray(pool_vecs), 10)
                return [pool_uids[j] for j in order], chosen, sent, received, 10 * len(chosen), True
            hits = [(c, h) for c in chosen for h in dense_top(raw_nodes[c][0], raw_nodes[c][2], q)]
            ranked = [u for _, (u, _) in sorted(hits, key=lambda x: -x[1][1])[:10]]
            return ranked, chosen, sent, received, 10 * len(chosen), True
        pool, received = [], 0
        for c in chosen:
            node, profile, uid_of = our_nodes[c]
            cand = psi_top(node, profile, uid_of, q, nprobe=nprobe)
            pool += [dict(p, uid=uid_of[p["document"]]) for p in cand]
            received += psi_table_bytes[c] + nprobe * 64       # full labeled PSI: every envelope, plus OPRF replies
        if hybrid and pool:
            order, s_ = hybrid_top(question, q, [p["document"] for p in pool], np.asarray([p["embedding"] for p in pool]), 10)
            ranked = [(pool[j]["document"], float(s_[j])) for j in order]
        else:
            ranked = rerank_passages(q, pool, top_n=10)
        by_doc = {p["document"]: p["uid"] for p in pool}
        sent = len(chosen) * (nprobe * 64 + 64)                # blinded points (hex) + framing
        return [by_doc[d] for d, _ in ranked], chosen, sent, received, len(pool), False

    rows = []
    per_query: dict[str, list[float]] = {}   # configuration -> per-query MRR (for paired bootstrap, docs/50)
    split: list[tuple[float, float]] = []   # blind: (device ms, slowest hospital ms) per question
    for name in [c for c in CONFIGS if args.only is None or c in args.only]:
        m, p, n, contacts, sent, recv, disclosed, exposed, patterns, times = ([] for _ in range(10))
        split.clear()
        for i, (qid, _, rel) in enumerate(queries):
            t_q = time.perf_counter()
            ranked, contacted, s_b, r_b, disc, text_sent = run(name, i)
            times.append((time.perf_counter() - t_q) * 1000)
            m.append(mrr(ranked, rel)); p.append(p_at(ranked, rel)); n.append(ndcg_at(ranked, rel))
            contacts.append(len(contacted)); sent.append(s_b); recv.append(r_b); disclosed.append(disc)
            exposed.append(1.0 if text_sent and contacted else 0.0)
            patterns.append(sorted(contacted))
        per_query[name] = [float(x) for x in m]
        half = len(queries) // 2
        topic_acc = float("nan")
        if CONFIGS[name][0] != "central":
            labels = sorted(set(topic))
            att = HistoryAttacker().fit(list(zip(patterns[:half], topic[:half])))
            topic_acc = evaluate(att, list(zip(patterns[half:], topic[half:])), labels)["accuracy"]
        rows.append({"configuration": name, "queries": len(queries),
                     "mrr": float(np.mean(m)), "p@10": float(np.mean(p)), "ndcg@10": float(np.mean(n)),
                     "mrr_second_half": float(np.mean(m[len(m) // 2:])),
                     "contacts": float(np.mean(contacts)), "query_text_to_hospitals": float(np.mean(exposed)),
                     "topic_inference": topic_acc,
                     "topic_majority_floor": max(Counter(topic[half:]).values()) / len(topic[half:]),
                     "passages_disclosed_per_query": float(np.mean(disclosed)),
                     "bytes_sent_per_query": float(np.mean(sent)), "bytes_received_per_query": float(np.mean(recv)),
                     "compute_ms_per_query": float(np.mean(times)), "compute_ms_p95": float(np.percentile(times, 95)),
                     "device_ms_per_query": float(np.mean([d for d, _ in split])) if split else float("nan"),
                     "slowest_hospital_ms_per_query": float(np.mean([h for _, h in split])) if split else float("nan"),
                     "offline_table_bytes_total": (float(sum(offline_bytes.values())) if CONFIGS[name][2] == "blind"
                                                   else 0.0)})
        r = rows[-1]
        print(f"  {name:<28} MRR {r['mrr']:.4f} (2nd half {r['mrr_second_half']:.4f}) nDCG@10 {r['ndcg@10']:.4f} | contacts {r['contacts']:.1f} "
              f"| q-text {r['query_text_to_hospitals']:.2f} | topic {r['topic_inference']:.3f} (floor {r['topic_majority_floor']:.3f}) "
              f"| passages {r['passages_disclosed_per_query']:.0f} | ms {r['compute_ms_per_query']:.1f} "
              f"| sent {r['bytes_sent_per_query']:.0f} B recv {r['bytes_received_per_query'] / 1e6:.2f} MB"
              + (f" | device {r['device_ms_per_query']:.1f} ms, slowest hospital {r['slowest_hospital_ms_per_query']:.1f} ms"
                 if split else ""), flush=True)

    # De-identification damage on clean clinical prose (no real PII present).
    for label, nodes in (("stock Presidio (HyFedRAG-style)", hy_nodes), ("rules + full-name NER (ours)", our_nodes)):
        if nodes is None:
            continue
        altered = total = 0
        for c in clients:
            orig = [t for _, t in client_docs[c]]
            altered += sum(1 for a, b in zip(orig, nodes[c][0].documents) if a != b)
            total += len(orig)
        rows.append({"configuration": f"deid: {label}", "docs_altered": altered / total})
        print(f"  deid {label:<32} documents altered {altered / total:.3f}", flush=True)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / f"hyfedrag_compare_{args.partition}_{time.strftime('%Y%m%d-%H%M%S')}.csv"
    out.with_suffix(".perquery.json").write_text(json.dumps({
        "partition": args.partition, "dirichlet_alpha": args.dirichlet_alpha, "seed": args.seed,
        "query_ids": [qid for qid, *_ in queries], "mrr": per_query}))
    with out.open("w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out} ({time.perf_counter() - t0:.0f}s)")


if __name__ == "__main__":
    main()
