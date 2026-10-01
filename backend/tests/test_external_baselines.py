"""Reproduced external baselines (baselines/external_fedrag.py, docs/53).

Checks that the copied pieces behave as their sources do on toy data; these
are not results.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from baselines.external_fedrag import flower_merge_documents


def test_flower_merge_ranks_by_ascending_l2_and_keeps_knn():
    docs, scores = ["a", "b", "c", "d"], [0.9, 0.1, 0.5, 0.3]
    assert flower_merge_documents(docs, scores, knn=3, k_rrf=60) == ["b", "d", "c"]
    assert flower_merge_documents(docs, scores, knn=2) == ["b", "d"]


def test_flower_client_index_finds_the_nearest_document():
    """Run in a subprocess: FAISS and torch each link their own OpenMP
    runtime, and the second to initialise aborts the process on macOS."""
    if importlib.util.find_spec("faiss") is None:     # not imported here, see above
        pytest.skip("faiss not installed")
    code = (
        "import numpy as np\n"
        "from baselines.external_fedrag import FlowerClientIndex\n"
        "x = np.random.default_rng(0).normal(size=(64, 8)).astype('float32')\n"
        "index = FlowerClientIndex([f'd{i}' for i in range(64)], x)\n"
        "index.index.nprobe = index.index.nlist\n"
        "assert index.search(x[17], 1)[0][0] == 'd17'\n"
    )
    env = {**os.environ, "OMP_NUM_THREADS": "1"}
    done = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[1], env=env,
                          capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr[-2000:]


def test_ragroute_router_learns_a_separable_assignment():
    pytest.importorskip("torch")
    pytest.importorskip("sklearn")
    from baselines.external_fedrag import RAGRouteRouter

    rng = np.random.default_rng(1)
    centroids = {"s0": np.array([1.0, 0, 0, 0]), "s1": np.array([0, 1.0, 0, 0]), "s2": np.array([0, 0, 1.0, 0])}

    def sample(n):
        qs, labels = [], []
        for _ in range(n):
            s = int(rng.integers(3))
            qs.append(centroids[f"s{s}"] + rng.normal(scale=0.1, size=4))
            labels.append({f"s{s}"})
        return qs, labels

    tq, tl = sample(120)
    vq, vl = sample(40)
    router = RAGRouteRouter(["s0", "s1", "s2"], centroids).fit(tq, tl, vq, vl, epochs=30)
    assert router.val_auc > 0.9
    assert router.route(centroids["s1"]) == ["s1"]
