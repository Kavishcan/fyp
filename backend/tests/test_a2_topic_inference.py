"""Query-topic inference attackers (docs/39): they measure what they claim
on synthetic patterns; they are not privacy results."""
from __future__ import annotations

from attacks.a2_topic_inference import HistoryAttacker, SetPriorAttacker, evaluate, jaccard, macro_f1


def test_history_attacker_learns_a_deterministic_pattern():
    history = [(["a", "b"], "t1")] * 20 + [(["c", "d"], "t2")] * 20
    attacker = HistoryAttacker().fit(history)
    assert attacker.rank(["a", "b"])[0] == "t1"
    assert attacker.rank(["c", "d"])[0] == "t2"
    result = evaluate(attacker, history, attacker.topics)
    assert result["accuracy"] == 1.0 and result["macro_f1"] == 1.0


def test_history_attacker_is_at_chance_when_patterns_are_uninformative():
    """Every topic contacts every source (broadcast): nothing to learn."""
    history = [(["a", "b", "c"], t) for t in ("t1", "t2", "t3") for _ in range(10)]
    attacker = HistoryAttacker().fit(history)
    result = evaluate(attacker, history, attacker.topics)
    assert abs(result["accuracy"] - 1 / 3) < 1e-9


def test_set_prior_attacker_guesses_among_contacted_domains():
    attacker = SetPriorAttacker({"a": "t1", "b": "t2", "c": "t3"}, seed=0)
    ranking = attacker.rank(["a", "c"])
    assert set(ranking) == {"t1", "t3"}


def test_macro_f1_and_jaccard():
    assert macro_f1(["x", "y"], ["x", "y"], ["x", "y"]) == 1.0
    assert macro_f1(["x", "y"], ["y", "x"], ["x", "y"]) == 0.0
    assert jaccard({1, 2}, {2, 3}) == 1 / 3
    assert jaccard(set(), set()) == 1.0
