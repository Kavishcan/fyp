"""Gap 3: how much source content is released beyond what is needed (docs/56).

The docs/46 PMC setup (5,000 patients, 8 k-means hospitals, rules + NER
de-identification, 986 queries). For each configuration, per question:

- records_unlocked     records whose text and embedding reach the device
- used_top10 / used_prompt   records in the final top-10 ranking / in the
                       generator prompt (evidence_top_k = 2, the studio default)
- release_ratio        records_unlocked / records in the prompt; and
                       excess_vs_top10 = records_unlocked - 10
- release_precision    share of unlocked records that are relevant (qrels)
- MRR (hybrid ranking)

Configurations: blind unlock at cluster granularity (docs per cluster, min
cluster size) = (10, 5) [the default, every earlier result], (5, 3), (3, 2),
each at P = 4, 8, 16, 24. Plus hyfedrag_style_hybrid (every hospital
returns its own top-10: 80 records to the server) for reference.

Finer clusters release fewer records per unlocked cluster but publish more
centroids, each standing for fewer patients (docs/35: never publish
document embeddings as centroids). Measured per granularity: cluster sizes,
and the share of published centroids within cosine 0.95 / 0.90 of a single
patient's embedding.

Run: python -m eval.run_release
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from collections import Counter

import numpy as np

from eval.embed_cache import CachedEmbedder
from eval.run_hyfedrag_compare import build_nodes, load, mrr
from eval.sweep import RESULTS_DIR
from nodes.embedding import SentenceTransformerEmbedder
from privacy.blind_unlock import NodeClusters, TableCache, plan_probes, unlock
from privacy.cluster_index import build_cluster_index, kmeans_unit
from privacy.deidentify import presidio_backend
from privacy.psi import PSINode
from router.hybrid_rerank import DEFAULT_WEIGHT, hybrid_scores


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--queries", type=int, default=1000)
    parser.add_argument("--granularity", nargs="*", default=["10:5", "5:5", "5:3", "3:2"],
                        help="docs_per_cluster:min_size")
    parser.add_argument("--probes", type=int, nargs="*", default=[4, 8, 16, 24])
    parser.add_argument("--prompt-k", type=int, default=2)
    args = parser.parse_args()

    t0 = time.perf_counter()
    corpus, queries = load(args.queries, 5000, 11)
    uids = list(corpus)
    bge = CachedEmbedder(SentenceTransformerEmbedder("BAAI/bge-base-en-v1.5"))
    vecs = bge.embed([corpus[u] for u in uids])
    vecs = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)
    qv = bge.embed([t for _, t, _ in queries])
    qv = qv / np.linalg.norm(qv, axis=1, keepdims=True)
    _, assign = kmeans_unit(vecs, 8, 11)
    client_docs: dict[str, list[tuple[str, str]]] = {}
    for u, a in zip(uids, assign.tolist()):
        client_docs.setdefault(f"hospital_{int(a)}", []).append((u, corpus[u]))
    clients = sorted(client_docs)
    nodes = build_nodes(client_docs, bge, 11, presidio_backend(), deidentify=True)
    uid_by_doc = {d: u for c in clients for d, u in nodes[c][2].items()}
    print(f"{len(queries)} queries, nodes built ({time.perf_counter() - t0:.0f}s)", flush=True)

    def hybrid_rank(question, q, docs, dvecs, k=10):
        if not docs:
            return []
        s = hybrid_scores(question, q, docs, np.asarray(dvecs), DEFAULT_WEIGHT)
        return list(np.argsort(-s)[:k])

    rows, per_query = [], {}

    def record(name, extra, rec):
        m = {k: float(np.mean(v)) for k, v in rec.items()}
        rows.append({"configuration": name, **extra, "queries": len(rec["mrr"]), "mrr": m["mrr"],
                     "records_unlocked": m["unlocked"], "records_unlocked_p95": float(np.percentile(rec["unlocked"], 95)),
                     "used_top10": m["top10"], "used_prompt": m["prompt"],
                     "release_ratio_vs_prompt": m["unlocked"] / max(m["prompt"], 1e-9),
                     "excess_vs_top10": m["unlocked"] - m["top10"], "release_precision": m["precision"],
                     "relevant_unlocked": m["relevant"]})
        per_query[name] = {"mrr": [round(float(x), 4) for x in rec["mrr"]], "unlocked": [int(x) for x in rec["unlocked"]]}
        r = rows[-1]
        print(f"  {name:<28} MRR {r['mrr']:.4f} | unlocked {r['records_unlocked']:.0f} (p95 {r['records_unlocked_p95']:.0f}) "
              f"| ratio vs prompt {r['release_ratio_vs_prompt']:.0f}x | excess vs top-10 {r['excess_vs_top10']:.0f} "
              f"| release precision {r['release_precision']:.4f}", flush=True)

    # Reference: every hospital returns its own top-10 (HyFedRAG-style, hybrid at hospital and server).
    pos = {u: i for i, u in enumerate(uids)}
    rec = {k: [] for k in ("mrr", "unlocked", "top10", "prompt", "precision", "relevant")}
    for i, (_, question, rel) in enumerate(queries):
        pool = []
        for c in clients:
            docs = [t for _, t in client_docs[c]]
            dv = vecs[[pos[u] for u, _ in client_docs[c]]]
            pool += [client_docs[c][j][0] for j in hybrid_rank(question, qv[i], docs, dv)]
        top = [pool[j] for j in hybrid_rank(question, qv[i], [corpus[u] for u in pool], vecs[[pos[u] for u in pool]])]
        relevant = sum(1 for u in pool if u in rel)
        rec["mrr"].append(mrr(top, rel)); rec["unlocked"].append(len(pool)); rec["top10"].append(len(top))
        rec["prompt"].append(min(args.prompt_k, len(top))); rec["relevant"].append(relevant)
        rec["precision"].append(relevant / max(len(pool), 1))
    record("hyfedrag_style_hybrid", {"granularity": "-", "probes": "-"}, rec)

    for spec in args.granularity:
        dpc, min_size = (int(x) for x in spec.split(":"))
        cache, blind_clusters, sizes, n_centroids = TableCache(), [], [], 0
        near = {0.95: 0, 0.97: 0, 0.99: 0}
        t_b = time.perf_counter()
        for c in clients:
            node = nodes[c][0]
            centroids, clusters = build_cluster_index(node.documents, node.routing_embeddings, seed=11,
                                                      docs_per_cluster=dpc, min_size=min_size)
            psi = PSINode(c)
            psi.build_table(clusters)
            cache.put(c, psi.blind_table())
            nodes[c][0].psi_release = psi
            ids = sorted(clusters)
            cent = np.asarray(centroids)[ids]
            blind_clusters.append(NodeClusters(c, ids, cent, ["public"] * len(ids)))
            sizes += [len(clusters[k]) for k in ids]
            unit_docs = np.asarray(node.routing_embeddings) / np.linalg.norm(node.routing_embeddings, axis=1, keepdims=True)
            unit_c = cent / np.linalg.norm(cent, axis=1, keepdims=True)
            best = (unit_c @ unit_docs.T).max(axis=1)
            for th in near:
                near[th] += int((best >= th).sum())
            n_centroids += len(ids)
        table_mb = sum(cache.tables[c].size_bytes() for c in clients) / 1e6
        info = {"granularity": spec, "centroids_published": n_centroids, "cluster_size_min": int(min(sizes)),
                "cluster_size_median": float(np.median(sizes)),
                **{f"centroids_within_{th}_of_a_patient": v / n_centroids for th, v in near.items()}, "table_mb": table_mb}
        print(f" granularity {spec}: {n_centroids} centroids, size min {min(sizes)} median {np.median(sizes):.0f}, "
              f"within 0.95/0.97/0.99 of a patient {near[0.95] / n_centroids:.3f}/{near[0.97] / n_centroids:.3f}/"
              f"{near[0.99] / n_centroids:.3f}, "
              f"tables {table_mb:.1f} MB ({time.perf_counter() - t_b:.0f}s)", flush=True)
        for P in args.probes:
            rec = {k: [] for k in ("mrr", "unlocked", "top10", "prompt", "precision", "relevant")}
            for i, (_, question, rel) in enumerate(queries):
                plan = plan_probes(qv[i], blind_clusters, P)
                pool = []
                for c in clients:
                    psi = nodes[c][0].psi_release
                    opened = unlock(plan, c, psi.evaluate_for(plan.points[c], ["public"]), cache)
                    pool += [p for cid in opened for p in opened[cid]]
                order = hybrid_rank(question, qv[i], [p["document"] for p in pool], [p["embedding"] for p in pool])
                top = [uid_by_doc[pool[j]["document"]] for j in order]
                unlocked = [uid_by_doc[p["document"]] for p in pool]
                relevant = sum(1 for u in unlocked if u in rel)
                rec["mrr"].append(mrr(top, rel)); rec["unlocked"].append(len(pool)); rec["top10"].append(len(top))
                rec["prompt"].append(min(args.prompt_k, len(top))); rec["relevant"].append(relevant)
                rec["precision"].append(relevant / max(len(pool), 1))
            record(f"blind_g{spec.replace(':', '-')}_P{P}_hybrid", {**info, "probes": P}, rec)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / f"release_{time.strftime('%Y%m%d-%H%M%S')}.csv"
    out.with_suffix(".perquery.json").write_text(json.dumps({
        "partition": "kmeans", "seed": 11, "query_ids": [q for q, *_ in queries],
        "mrr": {k: v["mrr"] for k, v in per_query.items()}, "unlocked": {k: v["unlocked"] for k, v in per_query.items()}}))
    with out.open("w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out} ({time.perf_counter() - t0:.0f}s)")


if __name__ == "__main__":
    main()
