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
    """Holds published source profiles and their trust state."""

    def __init__(self) -> None:
        self._profiles: dict[str, SourceProfile] = {}

    def publish(self, profile: SourceProfile, *, verify_signature: bool = True) -> None:
        if verify_signature and not self._signature_valid(profile):
            raise ValueError(f"rejected profile for {profile.source_id!r}: invalid signature")
        existing = self._profiles.get(profile.source_id)
        if existing is not None and profile.profile_version <= existing.profile_version:
            raise ValueError(
                f"rejected stale/duplicate profile for {profile.source_id!r}: "
                f"version {profile.profile_version} <= existing {existing.profile_version}"
            )
        self._profiles[profile.source_id] = profile

    def _signature_valid(self, profile: SourceProfile) -> bool:
        # Placeholder: real signing/verification is out of scope until sources
        # are untrusted network participants rather than local simulation.
        # Kept as an explicit hook so it is not silently skipped later.
        return True

    def get(self, source_id: str) -> SourceProfile | None:
        return self._profiles.get(source_id)

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
