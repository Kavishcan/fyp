"""Offline per-source profile construction (docs/03-architecture.md offline path).

PII removal runs before embedding — if it ran after, the embeddings would
encode the PII and the published centroids would inherit it. `redact_pii` is a
regex heuristic placeholder, not a validated de-identification method; it must
be replaced with a proper library or documented as a limitation before any
claim is made about protecting document content.
"""
from __future__ import annotations

import re
from typing import Callable

import numpy as np

from baselines.base import SourceProfile
from router.perturb import perturb_centroids

_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONE_RE = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b")
_SSN_LIKE_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def redact_pii(text: str) -> str:
    """Heuristic placeholder redaction. See module docstring caveat."""
    text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = _SSN_LIKE_RE.sub("[REDACTED_ID]", text)
    text = _PHONE_RE.sub("[REDACTED_PHONE]", text)
    return text


def bucket_document_count(count: int) -> str:
    """Coarse bucket rather than an exact count, since exact counts are
    themselves a fingerprint that narrows which real institution a source is.
    """
    if count <= 0:
        return "0"
    if count <= 100:
        return "1-100"
    if count <= 1_000:
        return "101-1000"
    if count <= 10_000:
        return "1001-10000"
    if count <= 100_000:
        return "10001-100000"
    return "100000+"


def kmeans(vectors: np.ndarray, k: int, rng: np.random.Generator, iters: int = 50) -> np.ndarray:
    """Minimal Lloyd's-algorithm k-means, numpy only (no sklearn dependency),
    so profile construction stays testable without the heavier optional deps.
    """
    vectors = np.asarray(vectors, dtype=np.float64)
    n = vectors.shape[0]
    if n == 0:
        raise ValueError("cannot cluster zero vectors")
    k = min(k, n)
    init_idx = rng.choice(n, size=k, replace=False)
    centroids = vectors[init_idx].copy()

    for _ in range(iters):
        distances = np.linalg.norm(vectors[:, None, :] - centroids[None, :, :], axis=-1)
        assignments = np.argmin(distances, axis=1)
        new_centroids = centroids.copy()
        for cluster in range(k):
            members = vectors[assignments == cluster]
            if len(members):
                new_centroids[cluster] = members.mean(axis=0)
        if np.allclose(new_centroids, centroids):
            centroids = new_centroids
            break
        centroids = new_centroids

    return centroids


def build_profile(
    source_id: str,
    document_embeddings: np.ndarray,
    *,
    k: int,
    sigma: float,
    rng: np.random.Generator,
    document_count: int,
    profile_version: int = 1,
    policy_labels: list | None = None,
    expected_latency_ms: float = 0.0,
) -> SourceProfile:
    """Build a published profile from a source's own (already-embedded, already
    PII-stripped) documents. Documents themselves never leave the source —
    only the perturbed centroids returned inside the SourceProfile do.
    """
    centroids = kmeans(document_embeddings, k, rng)
    noisy_centroids = perturb_centroids(centroids, sigma, rng)
    return SourceProfile(
        source_id=source_id,
        centroids=noisy_centroids,
        document_count_bucket=bucket_document_count(document_count),
        policy_labels=policy_labels or [],
        expected_latency_ms=expected_latency_ms,
        profile_version=profile_version,
    )


def embed_documents(documents: list[str], embedder: Callable[[list[str]], np.ndarray]) -> np.ndarray:
    """PII removal happens here, before `embedder` ever sees the text."""
    cleaned = [redact_pii(doc) for doc in documents]
    return np.asarray(embedder(cleaned), dtype=np.float64)
