"""Topic-key assignment for the anonymity-set stage.

Real implementation of "seeded by a hash of the query cluster"
(docs/04-router-design.md section 7): finds the single nearest centroid across
every registered source's profile and uses its identity as the topic key, so
repeated queries landing near the same centroid get the same topic-stable
decoy cover set — which is the property the whole mechanism depends on.
"""
from __future__ import annotations

import numpy as np

from baselines.base import SourceProfile


def assign_topic_key(query_embedding: np.ndarray, profiles: list[SourceProfile]) -> str:
    q = np.asarray(query_embedding, dtype=np.float64)
    q_norm = np.linalg.norm(q) or 1.0
    best_key = "no-sources"
    best_score = -float("inf")
    for profile in profiles:
        centroids = np.asarray(profile.centroids, dtype=np.float64)
        if centroids.size == 0:
            continue
        norms = np.linalg.norm(centroids, axis=1)
        norms = np.where(norms == 0, 1.0, norms)
        scores = (centroids @ q) / (norms * q_norm)
        idx = int(np.argmax(scores))
        if scores[idx] > best_score:
            best_score = float(scores[idx])
            best_key = f"{profile.source_id}:{idx}"
    return best_key
