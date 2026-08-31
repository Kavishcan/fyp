"""Empirical embedding perturbation.

Deliberately not named or claimed as differential privacy. DP requires a
defined sensitivity, an adjacency relation, and a proven privacy budget; this
module adds calibrated Gaussian noise and reports only measured resistance to
the specific evaluated attackers (A1, A2), per docs/04-router-design.md
section 6. Do not describe `sigma` as an epsilon.
"""
from __future__ import annotations

import numpy as np


def perturb_embedding(vector: np.ndarray, sigma: float, rng: np.random.Generator) -> np.ndarray:
    """Add i.i.d. Gaussian noise with standard deviation `sigma` to `vector`.

    `sigma == 0` returns `vector` unperturbed, which is the baseline condition
    in the privacy/utility sweep (docs/05-experiments.md).
    """
    vector = np.asarray(vector, dtype=np.float64)
    if sigma < 0:
        raise ValueError("sigma must be >= 0")
    if sigma == 0:
        return vector.copy()
    noise = rng.normal(loc=0.0, scale=sigma, size=vector.shape)
    return vector + noise


def perturb_centroids(centroids: np.ndarray, sigma: float, rng: np.random.Generator) -> np.ndarray:
    """Perturb every row of a (c x d) centroid matrix independently."""
    centroids = np.asarray(centroids, dtype=np.float64)
    if sigma == 0:
        return centroids.copy()
    noise = rng.normal(loc=0.0, scale=sigma, size=centroids.shape)
    return centroids + noise
