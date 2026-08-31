import random

from router.anonymity import add_decoys, topic_stable_sample


def test_topic_stable_sample_is_deterministic_for_same_topic_and_pool():
    pool = [f"s{i}" for i in range(20)]
    first = topic_stable_sample(pool, 5, topic_key="oncology")
    second = topic_stable_sample(pool, 5, topic_key="oncology")
    assert first == second


def test_topic_stable_sample_differs_across_topics_generally():
    pool = [f"s{i}" for i in range(50)]
    a = set(topic_stable_sample(pool, 5, topic_key="oncology"))
    b = set(topic_stable_sample(pool, 5, topic_key="cardiology"))
    assert a != b


def test_add_decoys_reaches_requested_total_size():
    real = ["a", "b"]
    candidates = real + [f"s{i}" for i in range(20)]
    dispatched = add_decoys(real, candidates, m=8, topic_key="oncology")
    assert len(dispatched) == 8
    assert set(real).issubset(set(dispatched))


def test_add_decoys_does_not_exceed_available_candidates():
    real = ["a"]
    candidates = ["a", "b", "c"]
    dispatched = add_decoys(real, candidates, m=10, topic_key="t")
    assert set(dispatched) == {"a", "b", "c"}


def test_add_decoys_requires_topic_key_or_rng():
    import pytest

    with pytest.raises(ValueError):
        add_decoys(["a"], ["a", "b"], m=2)


def test_topic_stable_decoys_are_reused_across_repeated_queries_same_topic():
    """This is the property the design depends on: without it, an observer
    intersecting decoy sets across repeated same-topic queries recovers the
    genuine sources by elimination.
    """
    real = ["a"]
    candidates = ["a"] + [f"s{i}" for i in range(30)]
    dispatched_1 = set(add_decoys(real, candidates, m=6, topic_key="oncology"))
    dispatched_2 = set(add_decoys(real, candidates, m=6, topic_key="oncology"))
    # Decoy membership (ignoring shuffle order) must match across repeats.
    assert dispatched_1 == dispatched_2


def test_random_decoys_vary_across_repeated_queries_same_topic():
    real = ["a"]
    candidates = ["a"] + [f"s{i}" for i in range(30)]
    rng1 = random.Random(1)
    rng2 = random.Random(2)
    dispatched_1 = set(add_decoys(real, candidates, m=6, rng=rng1))
    dispatched_2 = set(add_decoys(real, candidates, m=6, rng=rng2))
    assert dispatched_1 != dispatched_2
