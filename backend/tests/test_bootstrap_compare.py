"""Paired bootstrap (eval/bootstrap_compare.py). Not a result."""
import numpy as np

from eval.bootstrap_compare import paired_bootstrap


def test_identical_configurations_are_not_different():
    a = np.random.default_rng(0).random(500)
    r = paired_bootstrap(a, a.copy(), resamples=2000)
    assert r["difference"] == 0 and r["p_two_sided"] == 1.0 and r["ratio_ci95"][0] <= 1 <= r["ratio_ci95"][1]


def test_a_clear_paired_gap_is_significant_and_the_interval_excludes_zero():
    rng = np.random.default_rng(1)
    b = rng.random(500)
    r = paired_bootstrap(b + 0.05 + rng.normal(0, 0.01, 500), b, resamples=2000)
    assert r["p_two_sided"] < 0.01 and r["diff_ci95"][0] > 0
