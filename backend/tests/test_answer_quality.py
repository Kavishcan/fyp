import json

import pytest

from eval.answer_quality import answer_metrics, score
from eval.prepare_answer_study import capped_text, evidence_metrics, pilot_questions, token_chunks
from eval.run_smart_pilot import fingerprint


class WordTokenizer:
    def encode(self, text, add_special_tokens=False):
        return text.split()

    def decode(self, tokens, skip_special_tokens=True):
        return " ".join(tokens)


def test_chunks_overlap_and_context_cap():
    t = WordTokenizer()
    assert list(token_chunks("a b c d e", t, 3, 1)) == ["a b c", "c d e"]
    assert capped_text("a b c d", t, 2) == "a b"
    with pytest.raises(ValueError):
        list(token_chunks("text", t, 2, 2))


def test_multi_reference_metrics_and_missing_evidence():
    assert answer_metrics("The Sam Bankman-Fried.", ["Sam Bankman-Fried"])["exact_match"] == 1
    assert answer_metrics("New York", ["York", "New York"])["token_f1"] == 1
    assert answer_metrics("New York", ["York"])["token_f1"] == pytest.approx(2 / 3)
    assert answer_metrics("", ["Paris"]) == dict(exact_match=0, token_f1=0)
    assert evidence_metrics(["a", "a"], ["a"], ["a", "b"])["candidate_evidence_recall"] == .5
    assert evidence_metrics([], [], [])["all_final_evidence"] is None


def test_pilot_selection_is_order_independent_and_rejects_duplicates():
    rows = [dict(query_id=str(i)) for i in range(30)]
    assert pilot_questions(rows) == pilot_questions(list(reversed(rows)))
    assert len(pilot_questions(rows)) == 24
    with pytest.raises(ValueError):
        pilot_questions(rows + [rows[0]])


def setup_inputs(tmp_path):
    refs = [dict(query_id="q", method="hybrid", answers=["Paris"])]
    requests = [dict(query_id="q", method="hybrid", prompt="Question and retrieved text only")]
    for name, rows in (("answer-references.jsonl", refs), ("answer-requests.jsonl", requests)):
        (tmp_path / name).write_text("\n".join(map(json.dumps, rows)) + "\n")
    artifacts = {name: fingerprint(tmp_path / name) for name in ("answer-references.jsonl", "answer-requests.jsonl")}
    (tmp_path / "manifest.json").write_text(json.dumps(dict(completed=True, artifacts=artifacts)))
    (tmp_path / "generation.json").write_text(json.dumps(dict(model="unit-test-only", provider="fixture", temperature=0,
        max_output_tokens=128, requests_sha256=artifacts["answer-requests.jsonl"])))
    return tmp_path / "predictions.jsonl", tmp_path / "generation.json", tmp_path / "score.json"


def test_scoring_requires_exact_complete_coverage(tmp_path):
    pred, generation, output = setup_inputs(tmp_path)
    pred.write_text(json.dumps(dict(query_id="wrong", method="hybrid", answer="Paris")) + "\n")
    with pytest.raises(ValueError, match="exactly"):
        score(tmp_path, pred, generation, output)
    assert not output.exists()


def test_errors_are_zero_not_silently_dropped_and_no_overwrite(tmp_path):
    pred, generation, output = setup_inputs(tmp_path)
    pred.write_text(json.dumps(dict(query_id="q", method="hybrid", error="timeout")) + "\n")
    summary = score(tmp_path, pred, generation, output)
    assert summary["hybrid"]["failures"] == 1
    assert summary["hybrid"]["exact_match"] == 0
    with pytest.raises(ValueError, match="overwrite"):
        score(tmp_path, pred, generation, output)


def test_changed_requests_are_rejected(tmp_path):
    pred, generation, output = setup_inputs(tmp_path)
    (tmp_path / "answer-requests.jsonl").write_text("changed")
    with pytest.raises(ValueError, match="changed"):
        score(tmp_path, pred, generation, output)
