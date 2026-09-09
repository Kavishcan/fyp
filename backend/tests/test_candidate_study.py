import itertools

import numpy as np

from eval.run_candidate_study import oracle_prefix_hits, retrieval_metrics
from router.evidence_budget import AllocationConfig, AllocationResult, Candidate


def test_oracle_matches_exhaustive_prefix_enumeration():
    rankings = {"a": [0, 1, 2], "b": [3, 4, 5], "c": [6, 7]}
    relevant = {1, 2, 3, 7}
    for cap in range(4):
        for budget in range(7):
            expected = 0
            for lengths in itertools.product(*(range(len(r) + 1) for r in rankings.values())):
                if sum(lengths) > budget or sum(n > 0 for n in lengths) > cap:
                    continue
                hits = sum(len(set(r[:n]) & relevant) for r, n in zip(rankings.values(), lengths))
                expected = max(expected, hits)
            assert oracle_prefix_hits(rankings, relevant, cap, budget) == expected


def test_recall_counts_only_paid_returned_candidates_not_entire_source():
    result = AllocationResult(AllocationConfig(1, 1))
    result.contacted = ["source_000"]
    result.actions = [dict(returned=1, text_bytes=1, duplicate=0)]
    p = Candidate("source_000", "0", "text", np.ones(2))
    result.candidates = result.final = [p]
    metrics = retrieval_metrics(result, {0, 1}, np.array([0, 0]))
    assert metrics["source_recall"] == 1
    assert metrics["candidate_recall"] == .5
    assert metrics["document_recall_at_5"] == .5
