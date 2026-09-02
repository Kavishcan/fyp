import numpy as np
import pytest

from baselines.base import SourceProfile
from router.registry import NEUTRAL_TRUST_PRIOR, SourceRegistry, TrustEstimate


def test_unknown_source_gets_neutral_trust_prior():
    registry = SourceRegistry()
    estimate = registry.trust_estimate("nowhere")
    assert estimate.mean == NEUTRAL_TRUST_PRIOR
    assert estimate.observations == 0


def test_publish_then_get_round_trips():
    registry = SourceRegistry()
    profile = SourceProfile(source_id="a", centroids=np.array([[1.0, 0.0]]))
    registry.publish(profile)
    assert registry.get("a") is profile
    assert registry.source_ids() == ["a"]
    assert len(registry) == 1


def test_stale_profile_version_is_rejected():
    registry = SourceRegistry()
    registry.publish(SourceProfile(source_id="a", centroids=np.array([[1.0]]), profile_version=2))
    with pytest.raises(ValueError):
        registry.publish(SourceProfile(source_id="a", centroids=np.array([[1.0]]), profile_version=1))


def test_trust_estimate_penalised_shrinks_toward_neutral_prior_with_few_observations():
    estimate = TrustEstimate(mean=1.0, observations=1)
    penalised = estimate.penalised(min_observations=10)
    assert NEUTRAL_TRUST_PRIOR < penalised < 1.0


def test_trust_estimate_penalised_returns_mean_once_enough_observations():
    estimate = TrustEstimate(mean=0.9, observations=10)
    assert estimate.penalised(min_observations=10) == 0.9


def test_remove_deregisters_a_published_profile():
    registry = SourceRegistry()
    registry.publish(SourceProfile(source_id="a", centroids=np.array([[1.0, 0.0]])))
    assert registry.remove("a") is True
    assert registry.get("a") is None
    assert len(registry) == 0


def test_remove_unknown_source_returns_false():
    registry = SourceRegistry()
    assert registry.remove("nowhere") is False
