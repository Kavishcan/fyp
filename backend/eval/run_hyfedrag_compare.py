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
from privacy.psi import PSIClient
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
    parser.add_argument("--embedder-model", default="BAAI/bge-base-en-v1.5")
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
    client_of = {u: f"hospital_{int(a)}" for u, a in zip(uids, assign.tolist())}
    client_docs: dict[str, list[tuple[str, str]]] = {}
    for u in uids:
        client_docs.setdefault(client_of[u], []).append((u, corpus[u]))
    print(f"clients: {dict(sorted(Counter(client_of.values()).items()))} ({time.perf_counter() - t0:.0f}s)", flush=True)

    qv = embedder.embed([t for _, t, _ in queries])
    qv = qv / np.maximum(np.linalg.norm(qv, axis=1, keepdims=True), 1e-12)
    topic = [Counter(client_of[u] for u in rel).most_common(1)[0][0] for *_, rel in queries]

    # Centralized reference: exact dense retrieval over everything.
    def centralized(i):
        scores = vecs @ qv[i]
        return [uids[j] for j in np.argsort(-scores)[:10]]

    ner = presidio_backend()
    stock = presidio_backend(entities=("PERSON", "LOCATION"), full_names_only=False)
    print("building nodes: no de-id / stock Presidio (HyFedRAG-style) / rules + full-name NER (ours)", flush=True)
    raw_nodes = build_nodes(client_docs, embedder, args.seed, None, deidentify=False)
    hy_nodes = build_nodes(client_docs, embedder, args.seed, stock, deidentify=True)
    our_nodes = build_nodes(client_docs, embedder, args.seed, ner, deidentify=True)
    print(f"nodes ready ({time.perf_counter() - t0:.0f}s)", flush=True)

    clients = sorted(client_docs)
    from baselines.cosine_router import CosineRouter

    router = CosineRouter(aggregation="max")
    router.register_sources([our_nodes[c][1] for c in clients])
    cells = build_cells(clients, {c: c for c in clients}, args.cell_size)

    def run(name, i):
        q = qv[i]
        if name == "centralized":
            return centralized(i), [], 0, False
        if name == "hyfedrag_style":
            # HyFedRAG's edge retriever works over the hospital's raw local data
            # and de-identifies only what it sends on; so rank on the raw index
            # (its de-identification cost is reported separately below).
            hits = [h for c in clients for h in dense_top(raw_nodes[c][0], raw_nodes[c][2], q)]
            return [u for u, _ in sorted(hits, key=lambda x: -x[1])[:10]], clients, len(queries[i][1]) * len(clients), True
        if name == "cosine_router":
            chosen = list(router.rank(q, top_k=args.router_k).ranked_source_ids)
            hits = [h for c in chosen for h in dense_top(raw_nodes[c][0], raw_nodes[c][2], q)]
            return [u for u, _ in sorted(hits, key=lambda x: -x[1])[:10]], chosen, len(queries[i][1]) * len(chosen), True
        if name in ("ours_psi_cells", "ours_psi_top4"):
            if name == "ours_psi_cells":
                top = list(router.rank(q, top_k=1).ranked_source_ids)
                chosen = cell_cover(top, cells, max(len(c) for c in cells))
            else:   # PSI dispatch to the cosine top-k, no cells: isolates PSI's retrieval cost from the cells'
                chosen = list(router.rank(q, top_k=args.router_k).ranked_source_ids)
            pool, bytes_ = [], 0
            for c in chosen:
                node, profile, uid_of = our_nodes[c]
                cand = psi_top(node, profile, uid_of, q)
                pool += [dict(p, uid=uid_of[p["document"]]) for p in cand]
                bytes_ += 2 * 32 * 2 + 64          # two blinded points, hex-encoded, plus framing
            ranked = rerank_passages(q, pool, top_n=10)
            by_doc = {p["document"]: p["uid"] for p in pool}
            return [by_doc[d] for d, _ in ranked], chosen, bytes_, False
        raise ValueError(name)

    rows, per_q = [], {}
    for name in ("centralized", "hyfedrag_style", "cosine_router", "ours_psi_top4", "ours_psi_cells"):
        m, p, n, contacts, sent, exposed, patterns = [], [], [], [], [], [], []
        for i, (qid, _, rel) in enumerate(queries):
            ranked, contacted, bytes_, text_sent = run(name, i)
            m.append(mrr(ranked, rel)); p.append(p_at(ranked, rel)); n.append(ndcg_at(ranked, rel))
            contacts.append(len(contacted)); sent.append(bytes_); exposed.append(1.0 if text_sent and contacted else 0.0)
            patterns.append(sorted(contacted))
        half = len(queries) // 2
        topic_acc = float("nan")
        if name != "centralized":
            labels = sorted(set(topic))
            att = HistoryAttacker().fit(list(zip(patterns[:half], topic[:half])))
            topic_acc = evaluate(att, list(zip(patterns[half:], topic[half:])), labels)["accuracy"]
        rows.append({"configuration": name, "queries": len(queries),
                     "mrr": float(np.mean(m)), "p@10": float(np.mean(p)), "ndcg@10": float(np.mean(n)),
                     "contacts": float(np.mean(contacts)), "query_text_to_hospitals": float(np.mean(exposed)),
                     "topic_inference": topic_acc,
                     "topic_majority_floor": max(Counter(topic[half:]).values()) / len(topic[half:]),
                     "bytes_sent_per_query": float(np.mean(sent))})
        r = rows[-1]
        print(f"  {name:<16} MRR {r['mrr']:.4f} P@10 {r['p@10']:.4f} nDCG@10 {r['ndcg@10']:.4f} | contacts {r['contacts']:.1f} "
              f"| query text to hospitals {r['query_text_to_hospitals']:.2f} | topic inference {r['topic_inference']:.3f} "
              f"(floor {r['topic_majority_floor']:.3f}) | bytes {r['bytes_sent_per_query']:.0f}", flush=True)

    # De-identification damage on clean clinical prose (no real PII present).
    for label, nodes in (("stock Presidio (HyFedRAG-style)", hy_nodes), ("rules + full-name NER (ours)", our_nodes)):
        altered = total = 0
        for c in clients:
            orig = [t for _, t in client_docs[c]]
            altered += sum(1 for a, b in zip(orig, nodes[c][0].documents) if a != b)
            total += len(orig)
        rows.append({"configuration": f"deid: {label}", "docs_altered": altered / total})
        print(f"  deid {label:<32} documents altered {altered / total:.3f}", flush=True)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / f"hyfedrag_compare_{time.strftime('%Y%m%d-%H%M%S')}.csv"
    with out.open("w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out} ({time.perf_counter() - t0:.0f}s)")


if __name__ == "__main__":
    main()
