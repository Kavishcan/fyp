import numpy as np
import pytest

from eval.run_smart_pilot import measure_selection, partition_documents, summarize


def test_partition_balanced_reproducible_and_complete():
    one = partition_documents(13, 3, 42)
    assert np.array_equal(one, partition_documents(13, 3, 42))
    assert sorted(np.bincount(one)) == [4, 4, 5]
    with pytest.raises(ValueError):
        partition_documents(2, 3, 42)


def test_source_and_document_recall_use_distinct_ground_truth():
    assignment = np.array([0, 0, 1, 2])
    scores = np.array([0.9, 0.8, 0.7, 0.6])
    result = measure_selection([0, 2], {0, 2}, assignment, scores, top_n=1)
    assert result == {"contacts": 2, "source_recall": 0.5,
                      "document_recall_at_10": 0.5, "irrelevant_contacts": 1}
    empty = measure_selection([], {0, 2}, assignment, scores)
    assert empty["source_recall"] == empty["document_recall_at_10"] == 0


def test_summary_counts_all_violations_and_abstentions():
    rows = [{"method": "smart", "seed": seed, "contacts": 0, "source_recall": 0,
             "document_recall_at_10": 0, "irrelevant_contacts": 0, "routing_ms": 1,
             "budget_violation": False} for seed in [1, 2]]
    result = summarize(rows)[0]
    assert result["budget_violations"] == 0
    assert result["empty_selection_rate"] == 1
