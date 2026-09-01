"""Tests for eval/run_exposure_budget.py on tiny synthetic data — no real
BEIR download required.
"""
from __future__ import annotations

import numpy as np

from eval.run_exposure_budget import compute_specificity, run_condition
from router.exposure import ExposureWeights


def test_specificity_is_higher_when_similarity_is_concentrated():
    concentrated = np.array([0.9, 0.1, 0.1, 0.1])
    spread = np.array([0.5, 0.5, 0.5, 0.5])
    assert compute_specificity(concentrated) > compute_specificity(spread)


def test_specificity_of_single_candidate_is_zero():
    assert compute_specificity(np.array([0.7])) == 0.0


def test_run_condition_keeps_genuine_sources_regardless_of_budget():
    """The exposure budget must only ever truncate decoys — genuine sources
    are protected by construction (router/exposure.py's enforce_exposure_budget).
    Recall must therefore be identical whether or not a budget is applied.
    """
    from baselines.base import SourceProfile

    profiles = {
        "n1": SourceProfile(source_id="n1", centroids=np.array([[1.0, 0.0, 0.0]])),
        "n2": SourceProfile(source_id="n2", centroids=np.array([[0.0, 1.0, 0.0]])),
        "n3": SourceProfile(source_id="n3", centroids=np.array([[0.0, 0.0, 1.0]])),
        "n4": SourceProfile(source_id="n4", centroids=np.array([[0.7, 0.7, 0.0]])),
    }
    query_vectors = {
        "q1": np.array([1.0, 0.0, 0.0]),
        "q2": np.array([0.0, 1.0, 0.0]),
        "q3": np.array([0.0, 0.0, 1.0]),
    }
    relevant_nodes = {"q1": {"n1"}, "q2": {"n2"}, "q3": {"n3"}}

    no_budget = run_condition(
        profiles, query_vectors, relevant_nodes,
        coarse_k=4, top_k=1, m=3, exposure_budget=None, exposure_weights=ExposureWeights(), seed=0,
    )
    tight_budget = run_condition(
        profiles, query_vectors, relevant_nodes,
        coarse_k=4, top_k=1, m=3, exposure_budget=0.001, exposure_weights=ExposureWeights(), seed=0,
    )

    assert no_budget["mean_recall"] == tight_budget["mean_recall"]
    # a very tight budget should dispatch to fewer (or equal) nodes than no budget at all
    assert tight_budget["mean_nodes_contacted"] <= no_budget["mean_nodes_contacted"]
