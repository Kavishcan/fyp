from attacks.a3_hijack import local_hijack_trial
from router.trust import BoundedTrustUpdate


def test_local_hijack_trial_counts_selections_and_shape():
    topics = ["oncology"] * 10

    def select_fn(topic_key):
        return ["attacker", "honest1"]

    def evidence_relevance_fn(source_id, topic_key):
        return 0.1 if source_id == "attacker" else 0.9

    trust_update = BoundedTrustUpdate(alpha=0.3, decoy_aware=False)
    result = local_hijack_trial("attacker", topics, select_fn, evidence_relevance_fn, trust_update)

    assert result.total_queries == 10
    assert result.times_selected == 10
    assert result.selection_rate == 1.0


def test_local_hijack_trial_reflects_trust_decay_for_poor_evidence():
    topics = ["oncology"] * 5

    def select_fn(topic_key):
        return ["attacker"]

    def evidence_relevance_fn(source_id, topic_key):
        return 0.0

    trust_update = BoundedTrustUpdate(alpha=0.5, decoy_aware=False)
    local_hijack_trial("attacker", topics, select_fn, evidence_relevance_fn, trust_update)
    assert trust_update.get("attacker") < 0.5
