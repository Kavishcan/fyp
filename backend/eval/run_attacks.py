"""Real measured runs of A1 (query inversion) and A3 (routing hijack) —
docs/05-experiments.md's attack table, against the same real BEIR data and
real embedder eval/sweep.py uses. Before this script, both attacks existed
only as unit-tested code (synthetic vectors), the way A2 did before eval/sweep.py.

A1: attacks/a1_inversion.py's NearestNeighbourInversion, swept over the same
sigma grid as the routing sweep, using the real query pool itself as the
attacker's reference corpus (an honest-but-curious router trying to guess
which of the queries it has plausibly seen produced the perturbed embedding
it's holding).

A3: NOT attacks/a3_hijack.py's `local_hijack_trial` — that function's own
docstring says its numbers "must not be reported as" a real A3 result, since
it runs against this project's own router/trust.py prototype, not the actual
upstream TASR code. The real A3 here runs a forged-profile attacker through
baselines/tasr_adapter.py's real TASRAdapter across the real query stream,
with update_trust() called every query so trust genuinely evolves — this is
what CLAUDE.md's reproduction rule requires for a reportable A3 number.

Run: python -m eval.run_attacks
"""
from __future__ import annotations

import argparse
import csv
import random
import time
from pathlib import Path

import numpy as np

from attacks.a1_inversion import NearestNeighbourInversion, term_recovery_rate
from eval.sweep import (
    RESULTS_DIR,
    HashingEmbedder,
    SentenceTransformerEmbedder,
    _normalise,
    build_dataset,
    build_node_profiles,
)
from router.perturb import perturb_embedding


def run_a1_inversion(
    query_vectors: dict[str, np.ndarray],
    queries: dict[str, str],
    sigmas: list[float],
    seed: int,
) -> list[dict]:
    """Reference corpus = the real query pool itself (every query is both a
    potential target and a potential decoy for every other query) — a
    reasonably strong, self-consistent reference set built entirely from real
    text, not a fabricated one.
    """
    reference_ids = list(query_vectors)
    reference_texts = [queries[qid] for qid in reference_ids]
    reference_embeddings = np.array([query_vectors[qid] for qid in reference_ids])
    inverter = NearestNeighbourInversion(reference_texts, reference_embeddings)

    rng = np.random.default_rng(seed)
    rows = []
    for sigma in sigmas:
        term_rates = []
        exact_hits = 0
        for qid, true_text in queries.items():
            perturbed = perturb_embedding(query_vectors[qid], sigma, rng)
            recovered = inverter.recover(perturbed)
            term_rates.append(term_recovery_rate(recovered, true_text))
            if recovered == true_text:
                exact_hits += 1
        n = len(queries)
        rows.append(
            {
                "sigma": sigma,
                "n_queries": n,
                "mean_term_recovery": sum(term_rates) / n,
                "exact_recovery_rate": exact_hits / n,
            }
        )
    return rows


def run_a3_hijack(
    profiles: dict,
    node_docs: dict[str, list[str]],
    query_vectors: dict[str, np.ndarray],
    embedder,
    seed: int,
) -> dict:
    """One forged attacker node vs. the real 21-node honest pool, run through
    the real TASRAdapter with update_trust() called every query so
    reputation/consistency/agreement genuinely evolve over the stream.

    The attacker's published profile is forged to the mean of all real query
    embeddings (a generic "attractive to everyone" target — the classic
    hijack strategy). Its REAL registered evidence is a genuinely unrelated
    honest node's real documents, so the forged-profile-vs-actual-content
    mismatch TASR is designed to catch is real, not assumed.
    """
    from baselines.base import SourceProfile
    from baselines.tasr_adapter import TASRAdapter
    from nodes.simulator import forge_profile

    query_matrix = np.array(list(query_vectors.values()))
    mean_query_direction = _normalise(query_matrix.mean(axis=0))

    donor_node_id = next(iter(node_docs))  # arbitrary honest node lends its real (mismatched) content
    base_profile = profiles[donor_node_id]
    attacker_id = "attacker_forged"
    attacker_profile = forge_profile(base_profile, mean_query_direction.reshape(1, -1))
    attacker_profile.source_id = attacker_id

    honest_doc_embeddings = {node_id: embedder.embed(texts) for node_id, texts in node_docs.items()}
    doc_embeddings = dict(honest_doc_embeddings)
    doc_embeddings[attacker_id] = honest_doc_embeddings[donor_node_id]  # real content stays donor's, unrelated to the forged target

    tasr = TASRAdapter()
    all_profiles = list(profiles.values()) + [attacker_profile]
    tasr.register_sources(all_profiles, doc_embeddings=doc_embeddings)

    query_ids = list(query_vectors)
    random.Random(seed).shuffle(query_ids)
    n = len(query_ids)
    third = max(1, n // 3)

    selected_flags = []
    for qid in query_ids:
        qvec = query_vectors[qid]
        result = tasr.rank(qvec, top_k=2)
        selected = result.ranked_source_ids
        selected_flags.append(attacker_id in selected)
        tasr.update_trust(qvec, selected)

    early = selected_flags[:third]
    late = selected_flags[-third:]
    summary = tasr.trust_summary(malicious_source_ids=[attacker_id])

    return {
        "attacker_id": attacker_id,
        "n_queries": n,
        "overall_selection_rate": sum(selected_flags) / n,
        "early_third_selection_rate": sum(early) / len(early),
        "late_third_selection_rate": sum(late) / len(late),
        "malicious_reputation": summary["malicious_reputation"].get(
            tasr._source_to_id[attacker_id], None
        ),
        "honest_avg_reputation": summary["honest_avg_reputation"],
        "malicious_consistency": summary["malicious_consistency"].get(
            tasr._source_to_id[attacker_id], None
        ),
        "honest_avg_consistency": summary["honest_avg_consistency"],
    }


def run_rq03_defense_comparison(
    profiles: dict,
    node_docs: dict[str, list[str]],
    query_vectors: dict[str, np.ndarray],
    relevant_nodes: dict[str, set[str]],
    embedder,
    seed: int,
) -> list[dict]:
    """RQ03's actual question: does TASR's trust defense earn back the recall
    lost to a hijacker, compared to the same attack with no trust mechanism at
    all? Three conditions, same forged attacker, same real 849-query stream,
    same code path (baselines/tasr_adapter.py's real TASRAdapter) — only
    `defense_mode` and attacker presence differ, so the comparison isolates
    the defense's effect rather than confounding it with a different router.

    - "no_attacker": honest nodes only — the recall ceiling with no threat.
    - "attacker_no_defense": forged attacker present, defense_mode="none" —
      TASR's own reweighting fully disabled (a router with no trust mechanism
      at all, per CLAUDE.md's requirement that an unmodified condition must
      exist before any defended condition is measured against it).
    - "attacker_with_defense": forged attacker present, defense_mode="rel_cons_agr"
      (TASR's real default) — the actual defended condition.
    """
    from eval.metrics import recall_at_k
    from baselines.tasr_adapter import TASRAdapter
    from nodes.simulator import forge_profile

    query_matrix = np.array(list(query_vectors.values()))
    mean_query_direction = _normalise(query_matrix.mean(axis=0))
    donor_node_id = next(iter(node_docs))
    attacker_id = "attacker_forged"
    attacker_profile = forge_profile(profiles[donor_node_id], mean_query_direction.reshape(1, -1))
    attacker_profile.source_id = attacker_id

    honest_doc_embeddings = {node_id: embedder.embed(texts) for node_id, texts in node_docs.items()}
    doc_embeddings_with_attacker = dict(honest_doc_embeddings)
    doc_embeddings_with_attacker[attacker_id] = honest_doc_embeddings[donor_node_id]

    query_ids = list(query_vectors)
    random.Random(seed).shuffle(query_ids)
    n = len(query_ids)
    third = max(1, n // 3)

    def run_condition(condition_name: str, defense_mode: str, include_attacker: bool) -> dict:
        router = TASRAdapter(defense_mode=defense_mode)
        profs = list(profiles.values()) + ([attacker_profile] if include_attacker else [])
        docs = doc_embeddings_with_attacker if include_attacker else honest_doc_embeddings
        router.register_sources(profs, doc_embeddings=docs)

        recalls, attacker_hits = [], []
        for qid in query_ids:
            qvec = query_vectors[qid]
            selected = router.rank(qvec, top_k=2).ranked_source_ids
            recalls.append(recall_at_k(selected, relevant_nodes[qid]))
            if include_attacker:
                attacker_hits.append(attacker_id in selected)
            router.update_trust(qvec, selected)

        row = {
            "condition": condition_name,
            "overall_recall": sum(recalls) / n,
            "early_third_recall": sum(recalls[:third]) / third,
            "late_third_recall": sum(recalls[-third:]) / third,
        }
        if include_attacker:
            row["overall_attacker_selection_rate"] = sum(attacker_hits) / n
            row["early_third_attacker_rate"] = sum(attacker_hits[:third]) / third
            row["late_third_attacker_rate"] = sum(attacker_hits[-third:]) / third
        return row

    return [
        run_condition("no_attacker", "rel_cons_agr", include_attacker=False),
        run_condition("attacker_no_defense", "none", include_attacker=True),
        run_condition("attacker_with_defense", "rel_cons_agr", include_attacker=True),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpora", nargs="+", default=["arguana", "nfcorpus", "scifact", "fiqa", "trec-covid", "scidocs", "webis-touche2020"])
    parser.add_argument("--nodes-per-corpus", type=int, default=3)
    parser.add_argument("--docs-per-node", type=int, default=150)
    parser.add_argument("--n-queries-per-corpus", type=int, default=150)
    parser.add_argument("--sigmas", nargs="+", type=float, default=[0.0, 0.1, 0.25, 0.5, 1.0])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--embedder", choices=["sentence-transformer", "hashing"], default="sentence-transformer")
    parser.add_argument("--embedder-model", default="BAAI/bge-base-en-v1.5")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = time.strftime("%Y%m%d-%H%M%S")

    print(f"Loading {args.corpora}...")
    node_docs, queries, relevant_nodes, dropped = build_dataset(
        args.corpora, args.n_queries_per_corpus, args.docs_per_node, args.nodes_per_corpus, args.seed
    )
    print(f"{len(node_docs)} nodes, {len(queries)} queries ({dropped} dropped)")

    if args.embedder == "sentence-transformer":
        embedder = SentenceTransformerEmbedder(args.embedder_model)
        print(f"embedder: {args.embedder_model}")
    else:
        embedder = HashingEmbedder()
        print("embedder: hashing placeholder — NOT a reportable result")

    profiles = build_node_profiles(node_docs, embedder, k=3, seed=args.seed)

    print(f"embedding {len(queries)} queries...")
    query_ids = list(queries)
    raw_vectors = embedder.embed([queries[qid] for qid in query_ids])
    query_vectors = {qid: _normalise(vec) for qid, vec in zip(query_ids, raw_vectors)}

    print("\n=== A1: query inversion ===")
    a1_rows = run_a1_inversion(query_vectors, queries, args.sigmas, args.seed)
    a1_csv = RESULTS_DIR / f"a1_inversion_{run_id}.csv"
    with a1_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(a1_rows[0].keys()))
        writer.writeheader()
        writer.writerows(a1_rows)
    for row in a1_rows:
        print(f"  sigma={row['sigma']}: mean_term_recovery={row['mean_term_recovery']:.3f} "
              f"exact_recovery_rate={row['exact_recovery_rate']:.3f}")
    print(f"wrote {a1_csv}")

    print("\n=== A3: routing hijack (real TASRAdapter, forged profile) ===")
    a3_result = run_a3_hijack(profiles, node_docs, query_vectors, embedder, args.seed)
    a3_csv = RESULTS_DIR / f"a3_hijack_{run_id}.csv"
    with a3_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(a3_result.keys()))
        writer.writeheader()
        writer.writerow(a3_result)
    for k, v in a3_result.items():
        print(f"  {k}: {v}")
    print(f"wrote {a3_csv}")

    print("\n=== RQ03: does trust defense earn back the recall lost to a hijacker? ===")
    rq03_rows = run_rq03_defense_comparison(profiles, node_docs, query_vectors, relevant_nodes, embedder, args.seed)
    rq03_csv = RESULTS_DIR / f"rq03_defense_comparison_{run_id}.csv"
    fieldnames = sorted({key for row in rq03_rows for key in row})
    with rq03_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rq03_rows)
    for row in rq03_rows:
        print(f"  {row['condition']}: overall_recall={row['overall_recall']:.3f} "
              f"early_third_recall={row['early_third_recall']:.3f} late_third_recall={row['late_third_recall']:.3f}"
              + (f" | attacker_rate early={row.get('early_third_attacker_rate', float('nan')):.3f} "
                 f"late={row.get('late_third_attacker_rate', float('nan')):.3f}"
                 if "overall_attacker_selection_rate" in row else ""))
    print(f"wrote {rq03_csv}")


if __name__ == "__main__":
    main()
