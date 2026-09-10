"""Ed25519 profile signing and registry integrity controls (docs/30).

These verify tamper detection and key binding. They do NOT show that a signed
profile is truthful — a malicious node signs a forged profile just as validly
(see test_signed_forged_profile_still_verifies).
"""
from __future__ import annotations

import numpy as np
import pytest

from baselines.base import SourceProfile
from nodes.signing import (
    generate_private_key,
    load_or_create_key_file,
    private_key_bytes,
    public_key_bytes,
    sign_profile,
    verify_profile,
)
from router.registry import SourceRegistry


def _profile(source_id: str = "s0", centroids=None, version: int = 1) -> SourceProfile:
    return SourceProfile(
        source_id=source_id,
        centroids=np.array([[1.0, 0.0]]) if centroids is None else np.asarray(centroids, dtype=np.float64),
        profile_version=version,
    )


def test_sign_then_verify_round_trips():
    profile = sign_profile(_profile(), generate_private_key())
    assert profile.profile_signature and profile.public_key
    assert verify_profile(profile) is True


def test_unsigned_profile_does_not_verify():
    assert verify_profile(_profile()) is False


def test_tampered_centroids_break_the_signature():
    profile = sign_profile(_profile(), generate_private_key())
    profile.centroids = np.array([[0.0, 1.0]])
    assert verify_profile(profile) is False


def test_tampered_metadata_breaks_the_signature():
    profile = sign_profile(_profile(), generate_private_key())
    profile.topics = ["injected"]
    assert verify_profile(profile) is False


def test_signature_survives_a_float_round_trip():
    """Profiles cross a JSON boundary (MCP get_profile), so the payload must be
    stable under serialise/deserialise.
    """
    profile = sign_profile(_profile(centroids=[[0.123456789123, 0.9876543210]]), generate_private_key())
    revived = SourceProfile(
        source_id=profile.source_id,
        centroids=np.asarray(np.asarray(profile.centroids).tolist(), dtype=np.float64),
        profile_version=profile.profile_version,
        profile_signature=bytes.fromhex(profile.profile_signature.hex()),
        public_key=bytes.fromhex(profile.public_key.hex()),
    )
    assert verify_profile(revived) is True


def test_trust_fields_are_not_covered_by_the_signature():
    """Trust is coordinator-owned state, not a node's self-report, so updating
    it must not invalidate the node's signature.
    """
    profile = sign_profile(_profile(), generate_private_key())
    profile.trust_mean = 0.9
    profile.trust_observations = 12
    assert verify_profile(profile) is True


def test_signed_forged_profile_still_verifies():
    """The honest limit of signing: it proves integrity and key binding, never
    truthfulness. A3 self-misrepresentation is out of its scope.
    """
    forged = _profile(centroids=[[0.7071, 0.7071]])   # a deliberately generic attractor
    assert verify_profile(sign_profile(forged, generate_private_key())) is True


def test_key_file_is_created_once_and_reused(tmp_path):
    path = tmp_path / "node.key"
    first = load_or_create_key_file(path)
    second = load_or_create_key_file(path)
    assert private_key_bytes(first) == private_key_bytes(second)
    assert public_key_bytes(first) == public_key_bytes(second)


# --- registry integrity ----------------------------------------------------


def test_registry_accepts_unsigned_by_default():
    registry = SourceRegistry()
    registry.publish(_profile())
    assert registry.get("s0") is not None


def test_registry_rejects_a_present_but_invalid_signature_even_when_not_required():
    registry = SourceRegistry()
    profile = sign_profile(_profile(), generate_private_key())
    profile.centroids = np.array([[0.0, 1.0]])
    with pytest.raises(ValueError, match="invalid or missing signature"):
        registry.publish(profile)


def test_registry_can_require_signatures():
    registry = SourceRegistry(require_signatures=True)
    with pytest.raises(ValueError, match="invalid or missing signature"):
        registry.publish(_profile())
    registry.publish(sign_profile(_profile(source_id="s1"), generate_private_key()))
    assert registry.get("s1") is not None


def test_registry_rejects_republication_under_a_different_key():
    registry = SourceRegistry()
    registry.publish(sign_profile(_profile(version=1), generate_private_key()))
    impostor = sign_profile(_profile(version=2), generate_private_key())
    with pytest.raises(ValueError, match="public key changed"):
        registry.publish(impostor)


def test_registry_allows_republication_under_the_same_key():
    registry = SourceRegistry()
    key = generate_private_key()
    registry.publish(sign_profile(_profile(version=1), key))
    registry.publish(sign_profile(_profile(version=2), key))
    assert registry.get("s0").profile_version == 2


# --- plausibility ----------------------------------------------------------


def _spread_profiles(registry: SourceRegistry, n: int = 4) -> None:
    for i in range(n):
        centroid = np.zeros(4)
        centroid[i % 4] = 1.0
        registry.publish(SourceProfile(source_id=f"honest{i}", centroids=centroid[None, :]))


def test_plausibility_rejects_a_generic_attractor_profile():
    """The A3 forgery in eval/run_attacks.py publishes the mean of all queries,
    which lands close to the registry mean. This catches that specific shape.
    """
    registry = SourceRegistry(plausibility_threshold=0.9)
    _spread_profiles(registry)
    attacker = SourceProfile(source_id="attacker", centroids=np.ones((1, 4)) / 2.0)
    with pytest.raises(ValueError, match="implausibly generic"):
        registry.publish(attacker)


def test_plausibility_allows_a_normal_specific_profile():
    registry = SourceRegistry(plausibility_threshold=0.9)
    _spread_profiles(registry)
    honest = SourceProfile(source_id="new", centroids=np.array([[0.0, 0.0, 0.0, 1.0]]))
    registry.publish(honest)
    assert registry.get("new") is not None


def test_plausibility_needs_a_reference_population():
    """With too few registered profiles there is no meaningful mean to compare
    against, so the check abstains rather than guessing.
    """
    registry = SourceRegistry(plausibility_threshold=0.9)
    registry.publish(SourceProfile(source_id="only", centroids=np.ones((1, 4)) / 2.0))
    assert registry.get("only") is not None


def test_plausibility_is_off_by_default():
    registry = SourceRegistry()
    _spread_profiles(registry)
    registry.publish(SourceProfile(source_id="attacker", centroids=np.ones((1, 4)) / 2.0))
    assert registry.get("attacker") is not None
