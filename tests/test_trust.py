from router.trust import (
    BoundedTrustUpdate,
    TrustSignalInputs,
    TrustSignalWeights,
    compute_trust_signal,
)


def test_compute_trust_signal_is_normalised_to_unit_range():
    inputs = TrustSignalInputs(
        evidence_relevance=1.0,
        profile_consistency=1.0,
        cross_source_agreement=1.0,
        provenance_validity=1.0,
        service_reliability=1.0,
    )
    assert compute_trust_signal(inputs) == 1.0


def test_unmodified_trust_update_penalises_every_contacted_source_including_decoys():
    update = BoundedTrustUpdate(alpha=0.5, decoy_aware=False)
    update.update({"real": 0.9, "decoy": 0.1}, decoy_ids=frozenset({"decoy"}))
    assert update.get("real") == 0.7  # (1-0.5)*0.5 + 0.5*0.9
    assert update.get("decoy") == 0.3  # (1-0.5)*0.5 + 0.5*0.1


def test_decoy_aware_trust_update_exempts_flagged_decoys():
    update = BoundedTrustUpdate(alpha=0.5, decoy_aware=True)
    update.update({"real": 0.9, "decoy": 0.1}, decoy_ids=frozenset({"decoy"}))
    assert update.get("real") == 0.7
    assert update.get("decoy") == 0.5  # unchanged from default prior


def test_trust_is_bounded_to_unit_interval():
    update = BoundedTrustUpdate(alpha=1.0)
    update.update({"a": 5.0})
    assert update.get("a") == 1.0
    update.update({"a": -5.0})
    assert update.get("a") == 0.0
