"""Source-balanced centering of already-published routing profiles.

This is a label-free geometry transform, not a new privacy mechanism. Each
source gets one vote in the background vector, regardless of centroid count.
"""
from __future__ import annotations

import numpy as np


def normalize_rows(values):
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 2 or not np.isfinite(values).all():
        raise ValueError("vectors must be a finite matrix")
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    if not np.isfinite(norms).all():
        raise ValueError("vector norms must be finite")
    return np.divide(values, norms, out=np.zeros_like(values), where=norms != 0)


def center_profiles(profiles: dict[str, np.ndarray], strength: float):
    """Return a shared offset and normalized, transformed centroid matrices."""
    if not np.isfinite(strength) or not 0 <= strength <= 1:
        raise ValueError("centering strength must be in [0, 1]")
    if not profiles:
        return np.array([], dtype=float), {}
    units = {sid: normalize_rows(profiles[sid]) for sid in sorted(profiles)}
    if any(not len(v) for v in units.values()) or len({v.shape[1] for v in units.values()}) != 1:
        raise ValueError("profiles must be nonempty and share one embedding dimension")
    offset = strength * np.mean([v.mean(axis=0) for v in units.values()], axis=0)
    centered = {}
    for sid, vectors in units.items():
        shifted = vectors - offset
        shifted[np.linalg.norm(vectors, axis=1) == 0] = 0
        centered[sid] = normalize_rows(shifted)
    return offset, centered


def center_query(query, offset):
    query = np.asarray(query, dtype=np.float64)
    if query.ndim != 1 or query.shape != offset.shape or not query.size:
        raise ValueError("query and offset must have matching nonempty dimensions")
    unit = normalize_rows(query[None, :])[0]
    # A zero query must not become a meaningful negative-background query.
    if not np.any(unit):
        return unit
    return normalize_rows((unit - offset)[None, :])[0]
