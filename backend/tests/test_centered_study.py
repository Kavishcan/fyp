import numpy as np

from eval.run_centered_study import STRENGTHS, budget_config, centered_scores, normalized_text, select_strength
from router.centering import center_profiles


def test_selection_weights_datasets_equally_and_ties_prefer_raw():
    rows = [dict(dataset=d, strength=a, source_recall=.3, seed=s)
            for d in ("small", "large") for s in (11, 22, 33) for a in STRENGTHS]
    chosen, scores = select_strength(rows)
    assert chosen == 0
    assert all(abs(v - .3) < 1e-10 for v in scores.values())
    for row in rows:
        if row["strength"] == .5 and row["dataset"] == "small":
            row["source_recall"] = .5
    assert select_strength(rows)[0] == .5


def test_text_overlap_normalization():
    assert normalized_text("  Some\nQUERY ") == normalized_text("some query")


def test_zero_strength_scores_and_budget_filling_config():
    prepared = center_profiles({"a": np.eye(2)}, 0)
    assert centered_scores(np.array([1., 0.]), prepared) == {"a": 1.}
    cfg = budget_config(3, .5)
    assert cfg.exposure_budget == cfg.max_sources == 3
    assert cfg.relative_score_floor == cfg.minimum_gain == 0
