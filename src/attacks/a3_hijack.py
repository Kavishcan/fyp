"""A3: routing hijack — a malicious source forges its published profile to
attract queries it cannot serve well.

The real result must replicate Mu and Li's setup via baselines/tasr_adapter.py
once the upstream repository is cloned and verified (docs/10-baseline-selection.md).
`local_hijack_trial` below is a prototyping harness against this project's own
BoundedTrustUpdate (router/trust.py) — useful for developing the decoy-aware
exemption logic, but its numbers are not a substitute for the upstream TASR
result and must not be reported as one.
"""
from __future__ import annotations

from dataclasses import dataclass

from nodes.simulator import forge_profile
from router.trust import BoundedTrustUpdate


@dataclass
class HijackTrialResult:
    attacker_id: str
    times_selected: int
    total_queries: int

    @property
    def selection_rate(self) -> float:
        return self.times_selected / self.total_queries if self.total_queries else 0.0


def local_hijack_trial(
    attacker_id: str,
    query_topic_keys: list[str],
    select_fn,
    evidence_relevance_fn,
    trust_update: BoundedTrustUpdate,
) -> HijackTrialResult:
    """Run repeated queries, letting `select_fn(topic_key) -> list[source_id]`
    stand in for the pipeline's dispatch decision, and `evidence_relevance_fn`
    score what the attacker actually returns (expected to be poor, since it
    forged its profile rather than genuinely serving the topic). Trust is
    updated after every query, so this shows whether the trust layer
    suppresses the attacker over time.
    """
    times_selected = 0
    for topic_key in query_topic_keys:
        dispatched = select_fn(topic_key)
        if attacker_id in dispatched:
            times_selected += 1
            signals = {sid: evidence_relevance_fn(sid, topic_key) for sid in dispatched}
            trust_update.update(signals)
    return HijackTrialResult(
        attacker_id=attacker_id, times_selected=times_selected, total_queries=len(query_topic_keys)
    )


__all__ = ["HijackTrialResult", "local_hijack_trial", "forge_profile"]
