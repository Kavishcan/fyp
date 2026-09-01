"""Baseline-ladder sweep runner (docs/05-experiments.md "The sweep").

Wires the pieces that already existed in isolation — baselines/, router/,
attacks/a2_source_inference.py, eval/metrics.py, eval/instrument.py — into an
actual experiment over real BEIR queries and qrels (already downloaded under
backend/vendor/beir/), and writes a results table. Nothing here is simulated
text: corpus documents, queries and relevance judgments are the real BEIR
files.

Scope of this first sweep (deliberately not the full ladder in
docs/05-experiments.md yet):
  - Rung 0 (oracle) and rung 1 (broadcast) are each reported as a single
    condition — they do not go through the privacy pipeline, since oracle
    cheats by construction and broadcast has no ranking to perturb.
  - Rung 2/2.5 (official RAGRoute, HE routing) are NOT included: they need
    the vendor adapters wired against a real corpus, which is a separate,
    explicit step (CLAUDE.md "External code"). Not run, not estimated.
  - The local CosineRouter (the "transparent additional control", never
    presented as RAGRoute) is swept through PrivacyAwarePipeline over the
    two knobs docs/05-experiments.md names as "the sweep": `sigma` (query
    perturbation) and `m` (anonymity set size). This covers ladder rungs
    3 and 5 in one grid (sigma=0 is the rung-3 control point; m=top_k is
    the rung-5 control point).
  - Profile-noise (rung 4) and decoy-aware trust (rung 6, E1-E4) are NOT
    part of this grid — trust is held at a fixed neutral 0.5 for every
    candidate here, deliberately, so this sweep measures the
    perturbation/anonymity-set tradeoff in isolation. Trust dynamics need
    their own experiment (see router/trust.py's own module docstring on why
    an unmodified condition must exist first).

Node partitioning: two or more BEIR corpora are each split into
`nodes_per_corpus` nodes. A query's ground-truth relevant node(s) are derived
from the corpus's own qrels — not fabricated. Documents referenced by a
sampled query's qrels are always included in the node pool (so recall is
never trivially undefined); additional filler documents pad each node up to
`docs_per_node` for realistic profile construction. This directly gives the
"same-domain hard split" condition from docs/05-experiments.md's Known
confound section for free: with 3 nodes per corpus, the router must
distinguish between same-domain sources, not just between corpora.

A2 (source inference) topic key: BEIR ships no topic taxonomy, so this sweep
uses the query's own ground-truth relevant-node combination as its "topic".
This is a deliberate, explicit substitution for a real topic label — it
measures whether an observer can recover the identity of a node repeatedly
serving the same true routing outcome from the dispatch pattern alone, which
is the exact channel anonymity sets are meant to close. Only topic keys
observed 2+ times are informative for this attack and are reported as such.

Run: python -m eval.sweep --corpora arguana nfcorpus
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from attacks.a2_source_inference import SourceInferenceObserver, inference_accuracy
from baselines.base import SourceProfile
from baselines.broadcast import BroadcastRouter
from baselines.cosine_router import CosineRouter
from baselines.oracle import OracleRouter
from eval.instrument import Instrumentation, QueryLog
from eval.metrics import audit_cost, coarse_recall_at_k, ndcg_at_k, recall_at_k, reciprocal_rank
from nodes.embedding import HashingEmbedder, SentenceTransformerEmbedder
from nodes.profile import build_profile

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BEIR_DIR = REPO_ROOT / "backend" / "vendor" / "beir"
RESULTS_DIR = REPO_ROOT / "data" / "eval_results"


def _normalise(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    return vector / norm if norm > 0 else vector


# --- data loading (real BEIR files; each function is pure and independently
# testable on small in-memory dicts, see tests/test_eval_sweep.py) ----------


def load_qrels(corpus_dir: Path) -> dict[str, dict[str, int]]:
    if not corpus_dir.exists():
        raise FileNotFoundError(
            f"{corpus_dir} not found. Fetch it per docs/06-datasets.md before "
            f"running the sweep, e.g.: curl -o {corpus_dir.name}.zip "
            f"https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/"
            f"{corpus_dir.name}.zip"
        )
    qrels: dict[str, dict[str, int]] = defaultdict(dict)
    with (corpus_dir / "qrels" / "test.tsv").open() as f:
        next(f)  # header: query-id  corpus-id  score
        for line in f:
            qid, did, score = line.rstrip("\n").split("\t")
            score = int(score)
            if score > 0:
                qrels[qid][did] = score
    return dict(qrels)


def select_queries(
    corpus_dir: Path, qrels: dict[str, dict[str, int]], n_queries: int, rng: random.Random
) -> dict[str, str]:
    """Query id -> text, restricted to queries with at least one qrel, sampled
    deterministically down to `n_queries`.
    """
    judged_ids = set(qrels)
    selected: dict[str, str] = {}
    with (corpus_dir / "queries.jsonl").open() as f:
        for line in f:
            obj = json.loads(line)
            if obj["_id"] in judged_ids:
                selected[obj["_id"]] = obj["text"]
    ids = list(selected)
    rng.shuffle(ids)
    ids = ids[:n_queries]
    return {qid: selected[qid] for qid in ids}


def collect_documents(
    corpus_dir: Path,
    required_doc_ids: set[str],
    target_total: int,
    rng: random.Random,
) -> dict[str, str]:
    """doc_id -> text. Every id in `required_doc_ids` is guaranteed present;
    filler documents are added (up to `target_total`) so nodes have a
    realistic document count beyond just the qrels-referenced ones.
    """
    documents: dict[str, str] = {}
    filler_pool: list[tuple[str, str]] = []
    with (corpus_dir / "corpus.jsonl").open() as f:
        for line in f:
            obj = json.loads(line)
            doc_id = obj["_id"]
            title = obj.get("title", "").strip()
            text = obj.get("text", "").strip()
            full_text = f"{title}. {text}" if title else text
            if doc_id in required_doc_ids:
                documents[doc_id] = full_text
            elif len(filler_pool) < target_total * 3:
                filler_pool.append((doc_id, full_text))

    missing = required_doc_ids - documents.keys()
    if missing:
        raise ValueError(f"{len(missing)} required doc ids not found in {corpus_dir}/corpus.jsonl")

    needed_filler = max(0, target_total - len(documents))
    rng.shuffle(filler_pool)
    for doc_id, text in filler_pool[:needed_filler]:
        documents[doc_id] = text
    return documents


def partition_nodes(
    corpus_name: str, documents: dict[str, str], nodes_per_corpus: int, rng: random.Random
) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Returns (node_id -> [doc texts], doc_id -> node_id)."""
    doc_ids = list(documents)
    rng.shuffle(doc_ids)
    chunks = np.array_split(np.array(doc_ids, dtype=object), nodes_per_corpus)
    node_docs: dict[str, list[str]] = {}
    node_of_doc: dict[str, str] = {}
    for i, chunk in enumerate(chunks, start=1):
        node_id = f"{corpus_name}_{i}"
        node_docs[node_id] = [documents[d] for d in chunk]
        for d in chunk:
            node_of_doc[str(d)] = node_id
    return node_docs, node_of_doc


# --- profile / relevance construction --------------------------------------


def build_node_profiles(
    node_docs: dict[str, list[str]], embedder: HashingEmbedder, k: int, seed: int
) -> dict[str, SourceProfile]:
    profiles = {}
    for node_id, texts in node_docs.items():
        embeddings = embedder.embed(texts)
        profile = build_profile(
            node_id,
            embeddings,
            k=min(k, len(texts)),
            sigma=0.0,  # profile-noise (ladder rung 4) held at zero for this sweep
            rng=np.random.default_rng(seed),
            document_count=len(texts),
        )
        profiles[node_id] = profile
    return profiles


def make_feature_provider(profiles: dict[str, SourceProfile], query_vec: np.ndarray):
    from router.exposure import ExposureFactors
    from router.pipeline import RerankFeatures

    qn = _normalise(query_vec)

    def provider(candidate_ids):
        feats = {}
        for cid in candidate_ids:
            centroids = np.array([_normalise(c) for c in np.asarray(profiles[cid].centroids)])
            relevance = float(np.max(centroids @ qn)) if centroids.size else 0.0
            feats[cid] = RerankFeatures(
                relevance=relevance,
                trust=0.5,
                authorized=True,
                exposure_factors=ExposureFactors(0.0, 0.0, 0.0, 0.0),
                communication_cost=0.0,
                expected_latency=0.0,
                hijack_risk=0.0,
            )
        return feats

    return provider


# --- running one condition over the query stream ----------------------------


def _topic_key(relevant: set[str]) -> str:
    return "|".join(sorted(relevant)) if relevant else "unknown"


def run_plain_baseline(
    router,
    condition_name: str,
    query_vectors: dict[str, np.ndarray],
    relevant_nodes: dict[str, set[str]],
    instrumentation: Instrumentation,
    *,
    top_k: int = 0,
) -> dict:
    """No privacy pipeline — the router's own ranking, used as-is.

    `top_k=0` means "return everything the router ranks" for routers with that
    convention (oracle, broadcast). Not every router shares it — the real TASR
    adapter's upstream `route()` treats top_k=0 as "return nothing" (`list[:0]`
    is empty), so callers benchmarking TASR must pass an explicit top_k.
    """
    rows = []
    for qid, query_vec in query_vectors.items():
        relevant = relevant_nodes[qid]
        result = router.rank(query_vec, top_k=top_k, query_id=qid)
        dispatched = result.ranked_source_ids
        rows.append(
            dict(
                coarse_recall=recall_at_k(dispatched, relevant),
                final_recall=recall_at_k(dispatched, relevant),
                mrr=reciprocal_rank(dispatched, relevant),
                ndcg=ndcg_at_k(dispatched, relevant),
                audit_cost=audit_cost(dispatched, relevant),
                nodes_contacted=len(dispatched),
            )
        )
        instrumentation.record(
            QueryLog(
                query_id=f"{condition_name}:{qid}",
                topic_key=_topic_key(relevant),
                coarse_candidate_ids=dispatched,
                genuine_source_ids=dispatched,
                dispatched_source_ids=dispatched,
                surviving_source_ids=dispatched,
                extra={"condition": condition_name, "relevant_nodes": sorted(relevant)},
            )
        )
    return _summarise(condition_name, rows, sigma=None, m=None, n_queries=len(query_vectors))


def run_pipeline_condition(
    baseline_factory,
    profiles: dict[str, SourceProfile],
    condition_name: str,
    query_vectors: dict[str, np.ndarray],
    relevant_nodes: dict[str, set[str]],
    *,
    coarse_k: int,
    top_k: int,
    m: int,
    sigma: float,
    seed: int,
    instrumentation: Instrumentation,
) -> dict:
    from router.pipeline import PrivacyAwarePipeline, RerankWeights

    baseline = baseline_factory()
    baseline.register_sources(list(profiles.values()))
    pipeline = PrivacyAwarePipeline(baseline, rerank_weights=RerankWeights())
    rng = np.random.default_rng(seed)

    rows = []
    observer = SourceInferenceObserver()
    topic_ground_truth: dict[str, set[str]] = {}

    for qid, query_vec in query_vectors.items():
        relevant = relevant_nodes[qid]
        topic_key = _topic_key(relevant)
        topic_ground_truth[topic_key] = relevant

        result = pipeline.route(
            query_vec,
            coarse_k=coarse_k,
            top_k=top_k,
            m=m,
            topic_key=topic_key,
            feature_provider=make_feature_provider(profiles, query_vec),
            sigma=sigma,
            rng=rng,
        )

        rows.append(
            dict(
                coarse_recall=coarse_recall_at_k(result.coarse_candidate_ids, relevant),
                final_recall=recall_at_k(result.genuine_source_ids, relevant),
                mrr=reciprocal_rank(result.genuine_source_ids, relevant),
                ndcg=ndcg_at_k(result.genuine_source_ids, relevant),
                audit_cost=audit_cost(result.dispatched_source_ids, relevant),
                nodes_contacted=len(result.dispatched_source_ids),
            )
        )
        observer.observe(topic_key, result.dispatched_source_ids)
        instrumentation.record(
            QueryLog(
                query_id=f"{condition_name}:{qid}",
                topic_key=topic_key,
                coarse_candidate_ids=result.coarse_candidate_ids,
                genuine_source_ids=result.genuine_source_ids,
                dispatched_source_ids=result.dispatched_source_ids,
                surviving_source_ids=result.genuine_source_ids,
                extra={"condition": condition_name, "sigma": sigma, "m": m, "relevant_nodes": sorted(relevant)},
            )
        )

    repeated_topics = {
        k: v
        for k, v in topic_ground_truth.items()
        if sum(1 for q in query_vectors if _topic_key(relevant_nodes[q]) == k) >= 2
    }
    a2 = inference_accuracy(observer, repeated_topics) if repeated_topics else {"mean": float("nan")}

    summary = _summarise(condition_name, rows, sigma=sigma, m=m, n_queries=len(query_vectors))
    summary["a2_leakage_mean"] = a2["mean"]
    summary["a2_topics_evaluated"] = len(repeated_topics)
    return summary


def _summarise(condition_name, rows, *, sigma, m, n_queries) -> dict:
    def avg(key):
        return sum(r[key] for r in rows) / len(rows) if rows else float("nan")

    return {
        "condition": condition_name,
        "sigma": sigma,
        "m": m,
        "n_queries": n_queries,
        "coarse_recall": avg("coarse_recall"),
        "final_recall": avg("final_recall"),
        "mrr": avg("mrr"),
        "ndcg": avg("ndcg"),
        "audit_cost_mean": avg("audit_cost"),
        "nodes_contacted_mean": avg("nodes_contacted"),
        "a2_leakage_mean": float("nan"),
        "a2_topics_evaluated": 0,
    }


# --- top-level orchestration -------------------------------------------------


def build_dataset(corpora: list[str], n_queries_per_corpus: int, docs_per_node: int, nodes_per_corpus: int, seed: int):
    rng = random.Random(seed)
    all_node_docs: dict[str, list[str]] = {}
    node_of_doc: dict[str, str] = {}
    all_queries: dict[str, str] = {}
    qrels_by_corpus: dict[str, dict[str, dict[str, int]]] = {}

    for corpus_name in corpora:
        corpus_dir = BEIR_DIR / corpus_name
        qrels = load_qrels(corpus_dir)
        queries = select_queries(corpus_dir, qrels, n_queries_per_corpus, rng)
        required_doc_ids = {did for qid in queries for did in qrels[qid]}
        documents = collect_documents(corpus_dir, required_doc_ids, docs_per_node * nodes_per_corpus, rng)
        node_docs, doc_to_node = partition_nodes(corpus_name, documents, nodes_per_corpus, rng)

        all_node_docs.update(node_docs)
        node_of_doc.update(doc_to_node)
        for qid, text in queries.items():
            all_queries[f"{corpus_name}::{qid}"] = text
        qrels_by_corpus[corpus_name] = qrels

    relevant_nodes: dict[str, set[str]] = {}
    dropped = 0
    for namespaced_qid, text in list(all_queries.items()):
        corpus_name, qid = namespaced_qid.split("::", 1)
        qrels = qrels_by_corpus[corpus_name]
        relevant = {node_of_doc[did] for did in qrels[qid] if did in node_of_doc}
        if not relevant:
            dropped += 1
            del all_queries[namespaced_qid]
            continue
        relevant_nodes[namespaced_qid] = relevant

    return all_node_docs, all_queries, relevant_nodes, dropped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpora", nargs="+", default=["arguana", "nfcorpus", "scifact"])
    parser.add_argument("--nodes-per-corpus", type=int, default=3)
    parser.add_argument("--docs-per-node", type=int, default=150)
    parser.add_argument("--n-queries-per-corpus", type=int, default=100)
    parser.add_argument("--sigmas", nargs="+", type=float, default=[0.0, 0.1, 0.25, 0.5, 1.0])
    parser.add_argument("--ms", nargs="+", type=int, default=[2, 4, 6])
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument(
        "--coarse-k", type=int, default=None,
        help="default: max(largest m, half of total nodes), capped at total nodes. Decoys are only "
             "drawn from the coarse candidate pool (router/anonymity.py), so coarse_k < max(m) would "
             "silently cap the anonymity-set sweep — the default avoids that trap.",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument(
        "--embedder", choices=["sentence-transformer", "hashing"], default="sentence-transformer",
        help="hashing is the dependency-free placeholder (nodes/embedding.py) — fast for a smoke test, "
             "but per that module's own docstring must NOT be used for a reported leakage/routing result.",
    )
    parser.add_argument(
        "--embedder-model", default="BAAI/bge-base-en-v1.5",
        help="sentence-transformers model id, used only when --embedder=sentence-transformer. "
             "bge-base-en-v1.5 is retrieval-tuned (unlike the general-purpose MiniLM default it replaced).",
    )
    parser.add_argument(
        "--tasr-only", action="store_true",
        help="skip the cosine sigma x m grid entirely; run only oracle/broadcast/TASR. Much faster — "
             "useful for checking the real TASR reproduction without waiting on the full sweep.",
    )
    parser.add_argument(
        "--aggregation-ablation", action="store_true",
        help="instead of the sigma x m grid, run max/mean/top_r_mean each once at sigma=0, m=top_k "
             "(no privacy overhead) — CLAUDE.md: 'max-over-centroid is an ablation condition, not a "
             "default truth. Mean and top-r mean must be measured as alternatives.'",
    )
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = time.strftime("%Y%m%d-%H%M%S")
    out_csv = args.out or (RESULTS_DIR / f"sweep_{run_id}.csv")
    raw_log_path = RESULTS_DIR / f"sweep_{run_id}_raw.jsonl"
    instrumentation = Instrumentation(raw_log_path)

    print(f"Loading {args.corpora} (n_queries_per_corpus={args.n_queries_per_corpus}, "
          f"docs_per_node={args.docs_per_node}, nodes_per_corpus={args.nodes_per_corpus})...")
    node_docs, queries, relevant_nodes, dropped = build_dataset(
        args.corpora, args.n_queries_per_corpus, args.docs_per_node, args.nodes_per_corpus, args.seed
    )
    total_nodes = len(node_docs)
    default_coarse_k = min(total_nodes, max(max(args.ms, default=1), -(-total_nodes // 2)))
    coarse_k = args.coarse_k or default_coarse_k
    print(f"{total_nodes} nodes, {len(queries)} queries with ground truth "
          f"({dropped} dropped: relevant doc not in sampled pool). coarse_k={coarse_k}")

    if args.embedder == "sentence-transformer":
        embedder = SentenceTransformerEmbedder(args.embedder_model)
        print(f"embedder: {args.embedder_model} (real routing-quality result)")
    else:
        embedder = HashingEmbedder()
        print("embedder: hashing placeholder — NOT a reportable result, per nodes/embedding.py")

    profiles = build_node_profiles(node_docs, embedder, k=3, seed=args.seed)

    print(f"embedding {len(queries)} queries...")
    query_ids = list(queries)
    raw_vectors = embedder.embed([queries[qid] for qid in query_ids])
    query_vectors = {qid: _normalise(vec) for qid, vec in zip(query_ids, raw_vectors)}

    oracle_qrels = {qid: sorted(relevant_nodes[qid]) for qid in queries}

    results = []

    broadcast = BroadcastRouter()
    broadcast.register_sources(list(profiles.values()))
    results.append(run_plain_baseline(broadcast, "rung1_broadcast", query_vectors, relevant_nodes, instrumentation))

    oracle = OracleRouter(oracle_qrels)
    oracle.register_sources(list(profiles.values()))
    results.append(run_plain_baseline(oracle, "rung0_oracle", query_vectors, relevant_nodes, instrumentation))

    tasr_vendor_path = REPO_ROOT / "backend" / "vendor" / "routing-hijacking-fedrag"
    if tasr_vendor_path.exists():
        from baselines.tasr_adapter import TASRAdapter

        print("running rung6_tasr_real (no update_trust — routing formula only, see caveat below)...")
        tasr = TASRAdapter()
        tasr.register_sources(list(profiles.values()))
        results.append(
            run_plain_baseline(
                tasr, "rung6_tasr_real", query_vectors, relevant_nodes, instrumentation, top_k=args.top_k
            )
        )
        print(
            "  caveat: update_trust() was never called, so TASR's reputation/consistency/agreement "
            "signals stay at their registration defaults for every source — this benchmarks the real "
            "upstream mean-centroid routing formula, not trust dynamics (that's RQ03/E1-E4, separate)."
        )
    else:
        print(f"skipping TASR: {tasr_vendor_path} not cloned")

    if args.tasr_only:
        with out_csv.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
            writer.writeheader()
            writer.writerows(results)
        print(f"\nwrote {out_csv}")
        print(f"wrote raw per-query log {raw_log_path}")
        _print_table(results)
        return

    if args.aggregation_ablation:
        from baselines.cosine_router import AGGREGATIONS

        for aggregation in AGGREGATIONS:
            condition_name = f"cosine_aggregation_{aggregation}"
            print(f"running {condition_name}...")
            results.append(
                run_pipeline_condition(
                    lambda agg=aggregation: CosineRouter(aggregation=agg),
                    profiles,
                    condition_name,
                    query_vectors,
                    relevant_nodes,
                    coarse_k=coarse_k,
                    top_k=args.top_k,
                    m=args.top_k,
                    sigma=0.0,
                    seed=args.seed,
                    instrumentation=instrumentation,
                )
            )
        with out_csv.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
            writer.writeheader()
            writer.writerows(results)
        print(f"\nwrote {out_csv}")
        print(f"wrote raw per-query log {raw_log_path}")
        _print_table(results)
        return

    for sigma in args.sigmas:
        for m in args.ms:
            condition_name = f"cosine_pipeline_sigma{sigma}_m{m}"
            print(f"running {condition_name}...")
            results.append(
                run_pipeline_condition(
                    lambda: CosineRouter(aggregation="max"),
                    profiles,
                    condition_name,
                    query_vectors,
                    relevant_nodes,
                    coarse_k=coarse_k,
                    top_k=args.top_k,
                    m=m,
                    sigma=sigma,
                    seed=args.seed,
                    instrumentation=instrumentation,
                )
            )

    with out_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    print(f"\nwrote {out_csv}")
    print(f"wrote raw per-query log {raw_log_path}")
    _print_table(results)


def _print_table(results: list[dict]) -> None:
    headers = ["condition", "sigma", "m", "n_queries", "coarse_recall", "final_recall", "mrr", "ndcg",
               "audit_cost_mean", "nodes_contacted_mean", "a2_leakage_mean", "a2_topics_evaluated"]
    widths = {h: max(len(h), 12) for h in headers}
    print(" | ".join(h.ljust(widths[h]) for h in headers))
    for row in results:
        cells = []
        for h in headers:
            v = row[h]
            if isinstance(v, float):
                v = "n/a" if v != v else f"{v:.3f}"
            cells.append(str(v).ljust(widths[h]))
        print(" | ".join(cells))


if __name__ == "__main__":
    main()
