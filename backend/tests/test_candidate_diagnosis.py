import numpy as np
import pytest

from eval.diagnose_candidates import attribute


def test_exclusive_failure_stages():
    result = attribute({0, 1, 2, 3}, ["source_000"], {1, 2}, {2}, np.array([1, 0, 0, 0]))
    assert result == dict(source_miss=[0], depth_miss=[3], rerank_miss=[1], recovered=[2])
    assert sum(map(len, result.values())) == 4


def test_invalid_trace_rejected():
    with pytest.raises(ValueError):
        attribute({0}, [], [], [0], np.array([0]))
    with pytest.raises(ValueError):
        attribute({0}, [], [0], [0], np.array([0]))
    with pytest.raises(ValueError):
        attribute(set(), [], [], [], np.array([0]))
