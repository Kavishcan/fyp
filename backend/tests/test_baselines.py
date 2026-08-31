import numpy as np
import pytest

from baselines.base import SourceProfile
from baselines.broadcast import BroadcastRouter
from baselines.cosine_router import CosineRouter, aggregate_scores
from baselines.oracle import OracleRouter
from baselines.random_router import RandomRouter


def make_profiles():
    return [
        SourceProfile(source_id="a", centroids=np.array([[1.0, 0.0]])),
        SourceProfile(source_id="b", centroids=np.array([[0.0, 1.0]])),
        SourceProfile(source_id="c", centroids=np.array([[1.0, 1.0]])),
    ]


def test_broadcast_returns_all_sources_in_order():
    router = BroadcastRouter()
    router.register_sources(make_profiles())
    result = router.rank(np.array([1.0, 0.0]), top_k=0)
    assert result.ranked_source_ids == ["a", "b", "c"]


def test_broadcast_respects_top_k():
    router = BroadcastRouter()
    router.register_sources(make_profiles())
    result = router.rank(np.array([1.0, 0.0]), top_k=2)
    assert result.ranked_source_ids == ["a", "b"]


def test_random_router_returns_permutation_of_all_sources():
    router = RandomRouter(seed=0)
    router.register_sources(make_profiles())
    result = router.rank(np.array([1.0, 0.0]), top_k=0)
    assert set(result.ranked_source_ids) == {"a", "b", "c"}


def test_cosine_router_max_prefers_exact_match():
    router = CosineRouter(aggregation="max")
    router.register_sources(make_profiles())
    result = router.rank(np.array([1.0, 0.0]), top_k=1)
    assert result.ranked_source_ids == ["a"]


def test_cosine_router_rejects_unknown_aggregation():
    with pytest.raises(ValueError):
        CosineRouter(aggregation="bogus")


def test_aggregate_scores_max_vs_mean_differ_with_multiple_centroids():
    scores = np.array([0.9, 0.1])
    assert aggregate_scores(scores, "max") == pytest.approx(0.9)
    assert aggregate_scores(scores, "mean") == pytest.approx(0.5)


def test_oracle_router_requires_query_id():
    router = OracleRouter(qrels={"q1": ["a", "b"]})
    router.register_sources(make_profiles())
    with pytest.raises(ValueError):
        router.rank(np.array([1.0, 0.0]), top_k=2)


def test_oracle_router_returns_only_known_relevant_sources():
    router = OracleRouter(qrels={"q1": ["a", "z"]})
    router.register_sources(make_profiles())
    result = router.rank(np.array([1.0, 0.0]), top_k=5, query_id="q1")
    assert result.ranked_source_ids == ["a"]
