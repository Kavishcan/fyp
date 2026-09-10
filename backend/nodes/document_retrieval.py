"""Local-only diversity reranking; no labels or additional remote contacts."""
from collections import Counter
from dataclasses import dataclass
import math
import numpy as np


@dataclass(frozen=True)
class LocalRetrievalConfig:
    method: str = "cosine"
    pool_size: int = 64
    mmr_weight: float = .7

    def __post_init__(self):
        if self.method not in {"cosine", "parent_cap1", "parent_cap2", "mmr"}:
            raise ValueError("invalid local retrieval method")
        if type(self.pool_size) is not int or self.pool_size < 1:
            raise ValueError("pool_size must be a positive integer")
        if isinstance(self.mmr_weight, bool) or not math.isfinite(self.mmr_weight) or not 0 <= self.mmr_weight <= 1:
            raise ValueError("mmr_weight must be in [0,1]")


def rerank_local(order, scores, vectors, parent_ids, config=LocalRetrievalConfig()):
    """Reorder a fixed prefix and retain the tail, preserving stable pagination.

    Soft parent caps promote N chunks per document, then backfill skipped chunks
    in original relevance order. MMR uses cosine redundancy and stable ties.
    """
    order, scores = np.asarray(order, dtype=int), np.asarray(scores)
    if order.ndim != 1 or len(set(order.tolist())) != len(order):
        raise ValueError("order must contain unique indices")
    if len(order) and (order.min() < 0 or order.max() >= len(scores)):
        raise ValueError("order index outside scores")
    if not np.isfinite(scores).all():
        raise ValueError("nonfinite scores")
    if config.method == "cosine" or not len(order):
        return order.copy()
    pool, tail = order[:config.pool_size], order[config.pool_size:]
    if config.method.startswith("parent_cap"):
        if parent_ids is None or len(parent_ids) != len(scores) or any(not isinstance(p, str) or not p for p in parent_ids):
            raise ValueError("parent caps require one nonempty parent ID per chunk")
        counts, first, rest = Counter(), [], []
        for i in pool:
            parent = parent_ids[i]
            (first if counts[parent] < int(config.method[-1]) else rest).append(i)
            counts[parent] += 1
        return np.concatenate((first, rest, tail)).astype(int)
    values = np.asarray(vectors)[pool].astype(float)
    if values.ndim != 2 or not np.isfinite(values).all():
        raise ValueError("invalid vectors")
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    values = np.divide(values, norms, out=np.zeros_like(values), where=norms > 0)
    similarities = values @ values.T
    remaining, chosen = list(range(len(pool))), []
    redundancy = np.full(len(pool), -np.inf)
    while remaining:
        gains = config.mmr_weight * scores[pool]
        if chosen:
            gains = gains - (1 - config.mmr_weight) * redundancy
        i = max(remaining, key=lambda i: (gains[i], -i))
        chosen.append(i)
        remaining.remove(i)
        redundancy = np.maximum(redundancy, similarities[:, i])
    return np.concatenate((pool[chosen], tail))
