import numpy as np
import pytest

from router.discovery_completion import Passage, acquire, select_local


def test_budget_and_completion():
    parents = {str(i): str(i//2) for i in range(20)}
    def retrieve(s, parent, seen, known):
        c = select_local(list(parents), parents, parent, seen, known)
        return None if c is None else Passage(s, c, parents[c], "alpha", np.array([1., 0.]))
    result = acquire("alpha missing", [1., 0.], {"s": .8}, retrieve)
    assert len(result["actions"]) == 12
    assert len(result["final"]) == 5
    assert any(a["kind"] == "complete" for a in result["actions"])
    assert len({p.chunk_id for p in result["candidates"]}) == len(result["candidates"])
    assert all(a["kind"] == "discover" for a in acquire(
        "alpha missing", [1., 0.], {"s": .8}, retrieve, completion=False)["actions"])


def test_failed_calls_charged_and_closed():
    def broken(*args):
        raise RuntimeError("offline")
    r = acquire("test", [1.], {"a": .5, "b": .4}, broken, budget=1)
    assert len(r["actions"]) == 1 and r["actions"][0]["status"] == "error"
    assert not r["candidates"]


def test_wrong_source_rejected():
    r = acquire("test", [1.], {"a": .5}, lambda *args: Passage("b", "x", "p", "x", np.ones(1)))
    assert not r["candidates"] and len(r["actions"]) == 1


@pytest.mark.parametrize("budget", [-1, True, 1.5])
def test_invalid_budget(budget):
    with pytest.raises(ValueError):
        acquire("x", [1.], {}, lambda *args: None, budget=budget)


def test_empty_and_zero():
    assert not acquire("x", [1.], {}, None)["actions"]
    assert not acquire("x", [1.], {"s": .5}, None, budget=0)["actions"]


def test_node_selection():
    ids = ["a", "b", "c"]
    parents = dict(a="one", b="one", c="two")
    assert select_local(ids, parents, None, {"a"}, {"one"}) == "c"
    assert select_local(ids, parents, "one", {"a"}, {"one"}) == "b"
    assert select_local(ids, parents, "absent", set(), set()) is None


def test_invalid_embedding_and_parent_are_not_accepted():
    for embedding in (np.array([np.nan]), np.zeros(1), np.ones(2)):
        r = acquire("x", [1.], {"s": .5},
                    lambda *args: Passage("s", "c", "p", "x", embedding))
        assert not r["candidates"]


def test_fact_normalization_preserves_word_boundaries():
    from eval.run_discovery_completion import normalized
    assert normalized("Alice's -- 2024 report") == "alice s 2024 report"
    assert normalized("bank man") != normalized("bankman")
