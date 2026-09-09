import pytest
import json

from eval.run_feedback_study import STRENGTHS, choose_strength, validate_frozen
from eval.run_smart_pilot import fingerprint


def test_development_selection_uses_equal_dataset_weight_and_zero_tie_break():
    rows = [dict(dataset=d, strength=a, candidate_recall=.1)
            for d in ("a", "b") for a in STRENGTHS]
    assert choose_strength(rows)[0] == 0
    rows[2]["candidate_recall"] = .2
    assert choose_strength(rows)[0] == .25


def test_incomplete_development_grid_rejected():
    with pytest.raises(ValueError):
        choose_strength([])
    with pytest.raises(ValueError):
        choose_strength([dict(dataset="a", strength=0, candidate_recall=.1)])


def test_frozen_evaluation_rejects_modified_selection_inputs(tmp_path):
    development = tmp_path / "development.json"
    development.write_text("{}")
    path = tmp_path / "frozen.json"
    path.write_text(json.dumps(dict(strength=.1, development_sha256=fingerprint(development), code={})))
    assert validate_frozen(path)["strength"] == .1
    development.write_text('{"changed":true}')
    with pytest.raises(ValueError, match="Development results changed"):
        validate_frozen(path)
