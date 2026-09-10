"""Source profile registry (docs/04-router-design.md section 3).

New sources start at a neutral trust prior with an uncertainty penalty, not
full trust. Profiles carry a version and signature so drift, copied profiles,
and implausibly broad topic coverage can be checked before a profile is
trusted for routing.
"""
from __future__ import annotations

from dataclasses import dataclass

from baselines.base import SourceProfile

NEUTRAL_TRUST_PRIOR = 0.5


@dataclass
class TrustEstimate:
    """A trust value with an uncertainty penalty for low observation counts."""

    mean: float
    observations: int

    def penalised(self, min_observations: int = 10) -> float:
        """Shrink `mean` toward the neutral prior when observations are scarce."""
        if self.observations >= min_observations:
            return self.mean
        confidence = self.observations / min_observations
        return confidence * self.mean + (1 - confidence) * NEUTRAL_TRUST_PRIOR


class SourceRegistry:
    """Holds published source profiles and their trust state.

    Integrity controls (v2, docs/30):
    - A profile that carries a signature is always verified (nodes/signing.py);
      a present-but-invalid signature is rejected regardless of settings.
    - `require_signatures=True` additionally rejects unsigned profiles. Default
      False so legacy/simulated flows and existing experiments are unchanged.
    - Re-publication must come from the same public key as the existing entry
      (a third party cannot republish over a signed node).
    - `plausibility_threshold`, when set, rejects a new profile whose mean
      centroid is nearly identical to the mean of all already-registered
      profiles — the "generic attractor" shape the A3 forged profile in
      eval/run_attacks.py takes. This is a heuristic on published metadata,
      not a detection guarantee; a targeted forgery aimed at one topic passes it.
    """

    def __init__(self, *, require_signatures: bool = False, plausibility_threshold: float | None = None) -> None:
        if plausibility_threshold is not None and not 0.0 < plausibility_threshold <= 1.0:
            raise ValueError("plausibility_threshold must be in (0, 1]")
        self._profiles: dict[str, SourceProfile] = {}
        self.require_signatures = require_signatures
        self.plausibility_threshold = plausibility_threshold

    def publish(self, profile: SourceProfile, *, verify_signature: bool = True) -> None:
        if verify_signature and not self._signature_valid(profile):
            raise ValueError(f"rejected profile for {profile.source_id!r}: invalid or missing signature")
        existing = self._profiles.get(profile.source_id)
        if existing is not None and profile.profile_version <= existing.profile_version:
            raise ValueError(
                f"rejected stale/duplicate profile for {profile.source_id!r}: "
                f"version {profile.profile_version} <= existing {existing.profile_version}"
            )
        if existing is not None and existing.public_key and profile.public_key != existing.public_key:
            raise ValueError(f"rejected profile for {profile.source_id!r}: public key changed")
        reason = self.check_plausibility(profile)
        if reason is not None:
            raise ValueError(f"rejected profile for {profile.source_id!r}: {reason}")
        self._profiles[profile.source_id] = profile

    def _signature_valid(self, profile: SourceProfile) -> bool:
        from nodes.signing import verify_profile

        if profile.profile_signature or profile.public_key:
            return verify_profile(profile)
        return not self.require_signatures

    def check_plausibility(self, profile: SourceProfile) -> str | None:
        """None if acceptable, else a short rejection reason. Needs at least
        three other registered profiles to form a reference mean.
        """
        if self.plausibility_threshold is None:
            return None
        others = [p for sid, p in self._profiles.items() if sid != profile.source_id]
        if len(others) < 3:
            return None
        import numpy as np

        def mean_unit(centroids) -> np.ndarray | None:
            arr = np.asarray(centroids, dtype=np.float64)
            if arr.ndim != 2 or arr.size == 0 or not np.isfinite(arr).all():
                return None
            vector = arr.mean(axis=0)
            norm = np.linalg.norm(vector)
            return vector / norm if norm > 0 else None

        candidate = mean_unit(profile.centroids)
        reference_vectors = [v for v in (mean_unit(p.centroids) for p in others) if v is not None]
        if candidate is None or not reference_vectors:
            return None
        if any(v.shape != candidate.shape for v in reference_vectors):
            return None
        reference = np.mean(reference_vectors, axis=0)
        norm = np.linalg.norm(reference)
        if norm == 0:
            return None
        similarity = float(candidate @ (reference / norm))
        if similarity >= self.plausibility_threshold:
            return f"implausibly generic profile (cosine {similarity:.3f} to registry mean >= {self.plausibility_threshold})"
        return None

    def get(self, source_id: str) -> SourceProfile | None:
        return self._profiles.get(source_id)

    def remove(self, source_id: str) -> bool:
        """Deregister a published profile. Returns False if it wasn't present."""
        return self._profiles.pop(source_id, None) is not None

    def trust_estimate(self, source_id: str) -> TrustEstimate:
        profile = self._profiles.get(source_id)
        if profile is None:
            return TrustEstimate(mean=NEUTRAL_TRUST_PRIOR, observations=0)
        return TrustEstimate(mean=profile.trust_mean, observations=profile.trust_observations)

    def all_profiles(self) -> list[SourceProfile]:
        return list(self._profiles.values())

    def source_ids(self) -> list[str]:
        return list(self._profiles.keys())

    def __len__(self) -> int:
        return len(self._profiles)
