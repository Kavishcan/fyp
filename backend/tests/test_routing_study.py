import numpy as np

from baselines.base import SourceProfile
from eval.run_routing_study import attack_stream, clean_metrics, fixed_rank, paired_interval


def test_evidence_coverage_and_retrieval_recall_are_distinct():
    result = clean_metrics(["source_000"], {0, 11}, np.zeros(12, dtype=int), np.arange(12))
    assert result["source_recall"] == result["evidence_coverage"] == 1
    assert result["document_recall_at_10"] == .5


def test_fixed_control_includes_zero_score_ties():
    assert fixed_rank({"b": 0., "a": 0.}, 2) == ["a", "b"]


def test_bootstrap_pairs_queries_before_partitions():
    records = [dict(dataset="toy", scenario="clean", budget=3, query_id=q, seed=s,
                    method=m, source_recall=v) for q in ("a", "b") for s in (1, 2, 3)
               for m, v in (("candidate", .75), ("baseline", .5))]
    result = paired_interval(records, "toy", 3, "candidate", "baseline", "source_recall", 100)
    assert result["difference"] == .25
    assert result["ci95"] == [.25, .25]
    assert result["query_clusters"] == 2


def test_attack_selection_does_not_use_qrels_and_counts_attacker():
    documents = np.tile(np.eye(2), (30, 1))
    assignment = np.repeat(np.arange(30), 2)
    profiles = [SourceProfile(f"source_{i:03d}", np.array([[0., 1.]])) for i in range(30)]
    profiles[0].centroids = np.array([[1., 0.]])
    queries = np.tile(np.array([[1., 0.]]), (4, 1))
    ids = list("abcd")
    kwargs = dict(queries=queries, query_ids=ids, documents=documents, assignment=assignment,
                  profiles=profiles, seed=11, scenario="clone_empty", method="relative_evidence")
    a = list(attack_stream(qrels={q: {0} for q in ids}, **kwargs))
    b = list(attack_stream(qrels={q: {10} for q in ids}, **kwargs))
    assert [r["selected"] for r in a] == [r["selected"] for r in b]
    assert a[0]["malicious_contact"] == 1
    assert a[0]["contacts"] == 2
    assert all(r["contacts"] <= 3 and not r["budget_violation"] for r in a)
