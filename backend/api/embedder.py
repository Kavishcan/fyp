"""Deterministic, dependency-free placeholder embedder for the API layer.

Uses the hashing trick (fixed-size feature hashing) so vectors have a stable
dimensionality regardless of vocabulary growth, and the API can run without
the optional torch/sentence-transformers dependencies. This is NOT the
research pipeline's intended embedder — swap in a real sentence-embedding
model before any leakage or routing-quality result is reported. The research
code itself never hardcodes an embedder (see nodes/profile.py, nodes/simulator.py);
this class exists only because the API needs some default to be runnable.

`model_name` salts the hash, so two instances with different names produce
genuinely different, mutually incomparable vector spaces — even at the same
dimensionality. This simulates "different embedding models per node" honestly:
it is not a real model, but it reproduces the actual property that matters
(cross-model vectors don't compare), which is what the routing-embedder vs.
local-embedder split (README architecture note) needs to demonstrate.
"""
from __future__ import annotations

import hashlib
import re

import numpy as np

_TOKEN_RE = re.compile(r"[a-z0-9]+")

SHARED_ROUTING_MODEL = "shared-routing-embedder"


class HashingEmbedder:
    def __init__(self, model_name: str = SHARED_ROUTING_MODEL, n_features: int = 256) -> None:
        self.model_name = model_name
        self.n_features = n_features

    def _hash_index(self, token: str) -> int:
        digest = hashlib.sha256(f"{self.model_name}:{token}".encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "big") % self.n_features

    def embed_one(self, text: str) -> np.ndarray:
        vector = np.zeros(self.n_features, dtype=np.float64)
        for token in _TOKEN_RE.findall(text.lower()):
            vector[self._hash_index(token)] += 1.0
        return vector

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.array([self.embed_one(t) for t in texts], dtype=np.float64)

    def __call__(self, texts: list[str]) -> np.ndarray:
        return self.embed(texts)
