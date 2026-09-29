"""Session attack building blocks (eval/run_session_attack.py). Not results."""
from attacks.a2_topic_inference import HistoryAttacker
from eval.run_session_attack import session_chunks, source_attack


def test_session_chunks_split_a_summary_into_five_follow_ups():
    text = " ".join(f"Sentence number {i} has words." for i in range(12))
    chunks = session_chunks(text)
    assert len(chunks) == 5 and " ".join(chunks).count("Sentence") == 12
    assert session_chunks("Too short. Only two sentences here.") is None


def test_counting_finds_the_genuine_source_behind_random_decoys():
    session = [["g", "a", "b", "c"], ["g", "d", "e", "f"], ["g", "a", "h", "e"]]
    assert source_attack(session, "g") == 1.0
    assert source_attack([["g", "a"], ["g", "a"]], "g") == 0.5          # a fixed cover set: a tie


def test_constant_pattern_gives_the_session_attacker_nothing():
    everyone = ["a", "b", "c", "d"]
    att = HistoryAttacker().fit([(everyone, "t1")] * 30 + [(everyone, "t2")] * 10)
    assert att.rank_session([everyone] * 5)[0] == "t1"                  # the prior, nothing more
