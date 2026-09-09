import pytest

from eval.run_rich_profile_study import ALPHAS, select_alpha


def test_selection_weights_datasets_and_partition_kinds_equally():
    rows = [dict(dataset=d, kind=k, method="hybrid", alpha=a, candidate_recall=.1)
            for d in ("a", "b") for k in ("random", "topic") for a in ALPHAS]
    assert select_alpha(rows)[0] == 0
    rows[2]["candidate_recall"] = .2
    assert select_alpha(rows)[0] == .5


def test_incomplete_selection_grid_fails():
    with pytest.raises(ValueError):
        select_alpha([])
