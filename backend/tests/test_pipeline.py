import numpy as np

from baselines.base import SourceProfile
from baselines.cosine_router import CosineRouter
from router.exposure import ExposureFactors
from router.pipeline import PrivacyAwarePipeline, RerankFeatures, RerankWeights


def build_pipeline():
    profiles = [
        SourceProfile(source_id="a", centroids=np.array([[1.0, 0.0]])),
        SourceProfile(source_id="b", centroids=np.array([[0.9, 0.1]])),
        SourceProfile(source_id="c", centroids=np.array([[0.0, 1.0]])),
        SourceProfile(source_id="d", centroids=np.array([[-1.0, 0.0]])),
    ]
    baseline = CosineRouter(aggregation="max")
    baseline.register_sources(profiles)
    pipeline = PrivacyAwarePipeline(baseline, rerank_weights=RerankWeights())
    return pipeline


def feature_provider(candidate_ids):
    zero_exposure = ExposureFactors(0.0, 0.0, 0.0, 0.0)
    # "a" is the clearly relevant one; everyone else is mediocre.
    relevance = {"a": 1.0, "b": 0.5, "c": 0.1, "d": 0.0}
    return {
        cid: RerankFeatures(
            relevance=relevance.get(cid, 0.0),
            trust=0.5,
            authorized=True,
            exposure_factors=zero_exposure,
            communication_cost=0.0,
            expected_latency=0.0,
            hijack_risk=0.0,
        )
        for cid in candidate_ids
    }


def test_pipeline_selects_relevant_genuine_source():
    pipeline = build_pipeline()
    result = pipeline.route(
        np.array([1.0, 0.0]),
        coarse_k=4,
        top_k=1,
        m=3,
        topic_key="topic-1",
        feature_provider=feature_provider,
        rng=np.random.default_rng(0),
    )
    assert result.genuine_source_ids == ["a"]


def test_pipeline_dispatch_size_matches_m():
    pipeline = build_pipeline()
    result = pipeline.route(
        np.array([1.0, 0.0]),
        coarse_k=4,
        top_k=1,
        m=3,
        topic_key="topic-1",
        feature_provider=feature_provider,
        rng=np.random.default_rng(0),
    )
    assert len(result.dispatched_source_ids) == 3
    assert set(result.genuine_source_ids).issubset(set(result.dispatched_source_ids))


def test_pipeline_decoys_exclude_genuine_sources():
    pipeline = build_pipeline()
    result = pipeline.route(
        np.array([1.0, 0.0]),
        coarse_k=4,
        top_k=1,
        m=3,
        topic_key="topic-1",
        feature_provider=feature_provider,
        rng=np.random.default_rng(0),
    )
    assert "a" not in result.decoy_source_ids


def test_pipeline_respects_exposure_budget():
    pipeline = build_pipeline()

    def high_exposure_feature_provider(candidate_ids):
        base = feature_provider(candidate_ids)
        for cid, f in base.items():
            if cid != "a":
                f.exposure_factors = ExposureFactors(1.0, 1.0, 1.0, 1.0)
        return base

    result = pipeline.route(
        np.array([1.0, 0.0]),
        coarse_k=4,
        top_k=1,
        m=3,
        topic_key="topic-1",
        feature_provider=high_exposure_feature_provider,
        rng=np.random.default_rng(0),
        exposure_budget=2.0,
    )
    # "a" (protected, zero cost) must survive; decoys cost 4.0 each, so at most
    # zero of them fit inside the remaining budget.
    assert "a" in result.dispatched_source_ids
    assert len(result.dispatched_source_ids) == 1
