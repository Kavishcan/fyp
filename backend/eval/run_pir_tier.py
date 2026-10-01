"""Large-hospital tier: blind unlock with PIR fetch vs full table download (docs/55).

Part A (PMC, the docs/46 setup: 5,000 patients, 8 k-means hospitals, 986
queries, P = 8, hybrid ranking): tier 1 (download every table) and tier 2
(download hint + tag map, fetch the real clusters' sealed chunks with
SimplePIR) run on the same plans. Retrieval must be identical unless a
cluster is truncated. Measured: offline bytes, per-question bytes, hospital
ms (OPRF + PIR answer), device ms.

Part B (scaling): PIR cost depends only on the database shape, so it is
measured on random records of the blind-table record size at growing
database sizes (hint build, hint size, per-question answer time, query and
answer bytes). A 100 GB hospital is EXTRAPOLATED from the measured
throughput and the exact size formulas; it is not run.

Run: OMP_NUM_THREADS=1 python -m eval.run_pir_tier [--skip-pmc] [--sizes-mb 64 256 1024]
"""
from __future__ import annotations

import argparse
import csv
import os
import time
from collections import Counter

os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np

from eval.sweep import RESULTS_DIR
from privacy.pir import LWE_N, PIRClient, PIRServer, pack

RECORD = 16384 + 24 + 16             # one sealed blind-table chunk: CHUNK_BYTES + nonce + AEAD tag


def part_pmc(args, rows):
    from eval.embed_cache import CachedEmbedder
    from eval.run_hyfedrag_compare import build_nodes, load, mrr
    from nodes.embedding import SentenceTransformerEmbedder
    from privacy.blind_unlock import NodeClusters, TableCache, plan_probes, pir_unlock, unlock
    from privacy.cluster_index import kmeans_unit
    from privacy.deidentify import presidio_backend
    from router.hybrid_rerank import DEFAULT_WEIGHT, hybrid_scores

    t0 = time.perf_counter()
    corpus, queries = load(1000, 5000, 11)
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
    print(f"PMC nodes built ({time.perf_counter() - t0:.0f}s)", flush=True)

    cache, pir, table_bytes, hint_bytes, map_bytes, build_s = TableCache(), {}, 0, 0, 0, 0.0
    for c in clients:
        psi = nodes[c][0].psi
        cache.put(c, psi.blind_table())
        table_bytes += cache.tables[c].size_bytes()
        t_b = time.perf_counter()
        server, layout = psi.pir_database(per_column=args.per_column)
        hint = server.hint()
        build_s += time.perf_counter() - t_b
        pir[c] = (server, PIRClient(server.seed, hint, layout))
        hint_bytes += hint.nbytes
        map_bytes += layout.map_bytes()
    span = max(pir[c][1].layout.max_columns_per_group for c in clients)
    F = args.probes * span
    print(f"tier 1 tables {table_bytes / 1e6:.1f} MB | tier 2 hints {hint_bytes / 1e6:.1f} MB + maps "
          f"{map_bytes / 1e3:.0f} KB | columns per hospital {[pir[c][1].layout.cols for c in clients]} | "
          f"{F} PIR queries per hospital per question | hint build {build_s:.0f}s", flush=True)
    clusters = [NodeClusters(c, list(range(len(nodes[c][1].cluster_centroids))), np.asarray(nodes[c][1].cluster_centroids),
                             ["public"] * len(nodes[c][1].cluster_centroids)) for c in clients]
    uid_by_doc = {d: u for c in clients for d, u in nodes[c][2].items()}

    def rank(question, q, pool):
        if not pool:
            return []
        s = hybrid_scores(question, q, [p["document"] for p in pool], np.asarray([p["embedding"] for p in pool]),
                          DEFAULT_WEIGHT)
        return [uid_by_doc[pool[j]["document"]] for j in np.argsort(-s)[:10]]

    rec = {k: [] for k in ("mrr1", "mrr2", "same", "trunc", "hosp_oprf", "hosp_pir", "dev1", "dev2", "up2", "down2")}
    for i, (_, question, rel) in enumerate(queries[: args.pmc_queries]):
        plan = plan_probes(qv[i], clusters, args.probes)
        pool1, pool2, oprf_ms, pir_ms, dev1, dev2, up, down, trunc = [], [], [], [], 0.0, 0.0, 0, 0, 0
        for c in clients:
            t = time.perf_counter()
            evaluated = nodes[c][0].psi.evaluate_for(plan.points[c], ["public"])
            oprf_ms.append((time.perf_counter() - t) * 1000)
            t = time.perf_counter()
            got1 = unlock(plan, c, evaluated, cache)
            dev1 += (time.perf_counter() - t) * 1000
            server, client = pir[c]
            spent = []

            def answer(Q, server=server, spent=spent):
                t_s = time.perf_counter()
                out = server.answer(Q)
                spent.append((time.perf_counter() - t_s) * 1000)
                return out

            t = time.perf_counter()
            got2, stats = pir_unlock(plan, c, evaluated, client, answer, columns=F)
            dev2 += (time.perf_counter() - t) * 1000 - sum(spent)
            pir_ms.append(sum(spent))
            up += stats["query_bytes"]
            down += stats["answer_bytes"]
            trunc += stats["clusters_truncated"]
            pool1 += [p for cid in got1 for p in got1[cid]]
            pool2 += [p for cid in got2 for p in got2[cid]]
        r1, r2 = rank(question, qv[i], pool1), rank(question, qv[i], pool2)
        rec["mrr1"].append(mrr(r1, rel)); rec["mrr2"].append(mrr(r2, rel)); rec["same"].append(r1 == r2)
        rec["trunc"].append(trunc); rec["hosp_oprf"].append(max(oprf_ms)); rec["hosp_pir"].append(max(pir_ms))
        rec["dev1"].append(dev1); rec["dev2"].append(dev2); rec["up2"].append(up); rec["down2"].append(down)
    m = {k: float(np.mean(v)) for k, v in rec.items()}
    n_q = len(rec["mrr1"])
    for tier, mrr_v, off, up_b, down_b, hosp, dev in (
            ("tier1_full_download", m["mrr1"], table_bytes, 8 * (args.probes * 64 + 64), 8 * (args.probes * 64 + 64),
             m["hosp_oprf"], m["dev1"]),
            ("tier2_pir", m["mrr2"], hint_bytes + map_bytes, 8 * (args.probes * 64 + 64) + m["up2"],
             8 * (args.probes * 64 + 64) + m["down2"], m["hosp_oprf"] + m["hosp_pir"], m["dev2"])):
        rows.append({"part": "pmc", "configuration": tier, "queries": n_q, "probes": args.probes, "per_column": args.per_column,
                     "pir_queries_per_hospital": F if tier == "tier2_pir" else 0, "mrr": mrr_v,
                     "offline_bytes_total": off, "bytes_up_per_question": up_b, "bytes_down_per_question": down_b,
                     "slowest_hospital_ms": hosp, "device_unlock_ms": dev,
                     "identical_top10_share": m["same"], "clusters_truncated_per_question": m["trunc"]})
        r = rows[-1]
        print(f"  {tier:<20} MRR {mrr_v:.4f} | offline {off / 1e6:.1f} MB | up {up_b / 1e3:.1f} KB down {down_b / 1e3:.0f} KB "
              f"| slowest hospital {hosp:.1f} ms | device unlock {dev:.1f} ms | identical top-10 {m['same']:.3f} "
              f"| truncated {m['trunc']:.3f}", flush=True)


def part_scaling(args, rows):
    rng = np.random.default_rng(0)
    for size_mb in args.sizes_mb:
        n_records = int(size_mb * 1e6 // RECORD)
        per_column = max(1, -(-n_records // (1 << 16)))         # keep columns <= 65,536
        groups = [[(os.urandom(16), rng.integers(0, 256, RECORD, dtype=np.uint8).tobytes())] for _ in range(n_records)]
        D, layout = pack(groups, RECORD, per_column)
        del groups
        server = PIRServer(D)
        t = time.perf_counter()
        hint = server.hint()
        hint_s = time.perf_counter() - t
        client = PIRClient(server.seed, hint, layout)
        cols = rng.choice(layout.cols, size=args.probes, replace=False).tolist()
        t = time.perf_counter()
        built = [client.query(c) for c in cols]
        q_ms = (time.perf_counter() - t) * 1000
        Q = np.stack([q for q, _ in built])
        t = time.perf_counter()
        answers = server.answer(Q)
        a_ms = (time.perf_counter() - t) * 1000
        t = time.perf_counter()
        for (_, s), a in zip(built, answers):
            client.recover(a, s)
        r_ms = (time.perf_counter() - t) * 1000
        db = D.nbytes
        rows.append({"part": "scaling", "database_mb": db / 1e6, "records": n_records, "per_column": per_column,
                     "pir_rows": layout.rows, "pir_cols": layout.cols, "hint_mb": hint.nbytes / 1e6,
                     "map_mb": layout.map_bytes() / 1e6, "hint_build_s": hint_s, "queries": args.probes,
                     "query_mb": Q.nbytes / 1e6, "answer_mb": answers.nbytes / 1e6, "server_answer_ms": a_ms,
                     "client_query_ms": q_ms, "client_recover_ms": r_ms,
                     "server_gb_per_s": db * args.probes / 1e9 / (a_ms / 1000)})
        r = rows[-1]
        print(f"  DB {r['database_mb']:.0f} MB ({layout.rows} x {layout.cols}): hint {r['hint_mb']:.0f} MB built in "
              f"{hint_s:.0f}s, map {r['map_mb']:.2f} MB | {args.probes} queries: up {r['query_mb']:.2f} MB, down "
              f"{r['answer_mb']:.2f} MB, server {a_ms:.0f} ms ({r['server_gb_per_s']:.1f} GB/s of database x queries), "
              f"client {q_ms + r_ms:.0f} ms", flush=True)
        del D, server, client, hint


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--probes", type=int, default=8)
    parser.add_argument("--per-column", type=int, default=1)
    parser.add_argument("--pmc-queries", type=int, default=986)
    parser.add_argument("--sizes-mb", type=float, nargs="*", default=[64, 256, 1024])
    parser.add_argument("--skip-pmc", action="store_true")
    parser.add_argument("--skip-scaling", action="store_true")
    args = parser.parse_args()
    rows: list[dict] = []
    if not args.skip_pmc:
        part_pmc(args, rows)
    if not args.skip_scaling:
        part_scaling(args, rows)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / f"pir_tier_{time.strftime('%Y%m%d-%H%M%S')}.csv"
    with out.open("w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
