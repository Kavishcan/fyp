"""A1: query inversion by an honest-but-curious router.

Baseline attack: nearest-neighbour inversion against a reference corpus of
known (text, embedding) pairs. Given the perturbed query embedding the router
actually sees, find the reference text whose embedding is closest. This is a
weak, transparent baseline, not a trained inversion model — it establishes a
floor. A stronger attacker (e.g. a trained decoder) is future work and must
not be conflated with this baseline's numbers.
"""
from __future__ import annotations

import numpy as np


class NearestNeighbourInversion:
    def __init__(self, reference_texts: list[str], reference_embeddings: np.ndarray) -> None:
        if len(reference_texts) != len(reference_embeddings):
            raise ValueError("reference_texts and reference_embeddings must be the same length")
        self.reference_texts = reference_texts
        self.reference_embeddings = np.asarray(reference_embeddings, dtype=np.float64)

    def recover(self, observed_embedding: np.ndarray) -> str:
        q = np.asarray(observed_embedding, dtype=np.float64)
        q_norm = np.linalg.norm(q) or 1.0
        ref_norms = np.linalg.norm(self.reference_embeddings, axis=1)
        ref_norms = np.where(ref_norms == 0, 1.0, ref_norms)
        scores = (self.reference_embeddings @ q) / (ref_norms * q_norm)
        best = int(np.argmax(scores))
        return self.reference_texts[best]


def term_recovery_rate(recovered_text: str, true_query_text: str) -> float:
    """Jaccard overlap of lowercased whitespace tokens — a simple, transparent
    proxy for "how much of the query's intent leaked," not a claim of exact
    reconstruction.
    """
    recovered_tokens = set(recovered_text.lower().split())
    true_tokens = set(true_query_text.lower().split())
    if not true_tokens:
        return 0.0
    union = recovered_tokens | true_tokens
    if not union:
        return 0.0
    return len(recovered_tokens & true_tokens) / len(union)
