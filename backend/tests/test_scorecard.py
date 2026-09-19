"""Scorecard assembly: copies numbers, never computes them, blanks what is missing."""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from eval import scorecard


def _write(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as handle:
        w = csv.DictWriter(handle, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def test_merged_prefers_newest_per_key_without_dropping_older_conditions(tmp_path, monkeypatch):
    monkeypatch.setattr(scorecard, "RESULTS_DIR", tmp_path)
    _write(tmp_path / "leakage_20260101-000000.csv", [{"condition": "broadcast", "topic_engine_acc_mean": "0.06"},
                                                       {"condition": "cosine@K", "topic_engine_acc_mean": "0.40"}])
    import os, time
    time.sleep(0.01)
    newer = tmp_path / "leakage_20260102-000000.csv"
    _write(newer, [{"condition": "cosine@K", "topic_engine_acc_mean": "0.45"}])
    os.utime(newer, None)
    table, files = scorecard.merged("leakage", "condition")
    by = {r["condition"]: r for r in table}
    assert by["cosine@K"]["topic_engine_acc_mean"] == "0.45"   # newest wins
    assert by["broadcast"]["topic_engine_acc_mean"] == "0.06"  # older condition kept
    assert len(files) == 2


def test_assemble_blanks_missing_harnesses_and_copies_present_ones(tmp_path, monkeypatch):
    monkeypatch.setattr(scorecard, "RESULTS_DIR", tmp_path)
    _write(tmp_path / "leakage_20260101-000000.csv", [
        {"condition": c, "topic_engine_acc_mean": v, "source_attack_acc_mean": "0.5", "captured_gain_mean": "0.7"}
        for c, v in (("cosine@K", "0.45"), ("cells_1x4", "0.20"), ("sticky_decoys", "0.49"), ("broadcast", "0.06"), ("oracle", "0.44"))])
    table, sources = scorecard.assemble()
    by = {r["configuration"]: r for r in table}
    assert by["+ anonymity cells"]["topic_attack_feb4rag"] == pytest.approx(0.20)
    assert by["normal cosine router (top-k, no decoys)"]["topic_attack_feb4rag"] == pytest.approx(0.45)
    assert by["+ anonymity cells"]["answer_accuracy_mirage"] is None     # harness not run -> blank
    assert "MISSING" in sources["answer_quality"]


def test_markdown_renders_blanks_and_sources():
    table = [{"configuration": "a", "x": 0.5, "y": None}, {"configuration": "b", "x": None, "y": 1.0, "z": 2.0}]
    md = scorecard.to_markdown(table, {"leakage": "f.csv"})
    assert "| a | 0.500 |  |" in md and "f.csv" in md
