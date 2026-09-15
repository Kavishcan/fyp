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


# --- fixed anonymity cells (docs/40) -----------------------------------------

from router.anonymity import build_cells, cell_cover  # noqa: E402


def test_cells_are_domain_diverse_and_cover_every_source():
    groups = {f"a{i}": "A" for i in range(4)} | {f"b{i}": "B" for i in range(4)} | {f"c{i}": "C" for i in range(4)}
    cells = build_cells(list(groups), groups, cell_size=3)
    assert sorted(s for c in cells for s in c) == sorted(groups)
    assert all(len({groups[s] for s in cell}) == 3 for cell in cells)


def test_short_final_cell_is_merged():
    cells = build_cells([f"s{i}" for i in range(7)], {}, cell_size=3)
    assert [len(c) for c in cells] == [3, 4]


def test_cell_cover_dispatches_whole_cells_only():
    cells = [["a", "b"], ["c", "d"], ["e", "f"]]
    assert cell_cover(["a"], cells, max_sources=4) == ["a", "b"]
    assert cell_cover(["a", "c"], cells, max_sources=4) == ["a", "b", "c", "d"]
    assert cell_cover(["a", "c", "e"], cells, max_sources=4) == ["a", "b", "c", "d"]   # third cell does not fit
    assert cell_cover(["a", "b"], cells, max_sources=4) == ["a", "b"]                  # same cell once


def test_cell_cover_is_identical_for_every_query_landing_on_the_cell():
    cells = build_cells([f"s{i}" for i in range(8)], {}, cell_size=4)
    assert cell_cover([cells[0][0]], cells, 4) == cell_cover([cells[0][3]], cells, 4)
