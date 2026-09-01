"""Tests for eval/run_interference.py (E1: decoy trust decay) on tiny
synthetic data — no real BEIR download required.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from eval.run_interference import run_e1_decoy_trust_decay
from nodes.embedding import HashingEmbedder

_TASR_VENDOR_PATH = Path(__file__).resolve().parent.parent / "vendor" / "routing-hijacking-fedrag"


@pytest.mark.skipif(not _TASR_VENDOR_PATH.exists(), reason="upstream TASR repo not cloned")
def test_e1_decoy_trust_decay_runs_end_to_end():
    from baselines.base import SourceProfile

    embedder = HashingEmbedder(n_features=32)
    node_texts = {
        "n1": ["cats are small furry animals", "kittens are baby cats"],
        "n2": ["dogs are loyal furry animals", "puppies are baby dogs"],
        "n3": ["stock markets rise and fall", "shares trade on exchanges"],
        "n4": ["interest rates affect markets", "central banks set rates"],
    }
    profiles = {
        nid: SourceProfile(source_id=nid, centroids=embedder.embed(texts))
        for nid, texts in node_texts.items()
    }
    queries = {
        f"q{i}": text
        for i, text in enumerate(
            [
                "small furry pets",
                "baby animals",
                "stock market trading",
                "central bank interest rates",
            ]
            * 3
        )
    }
    query_vectors = {}
    for qid, text in queries.items():
        vec = embedder.embed_one(text)
        norm = np.linalg.norm(vec)
        query_vectors[qid] = vec / norm if norm else vec
    relevant_nodes = {}
    for qid, text in queries.items():
        if "pet" in text or "baby" in text and "animal" in text:
            relevant_nodes[qid] = {"n1", "n2"}
        elif "stock" in text:
            relevant_nodes[qid] = {"n3"}
        else:
            relevant_nodes[qid] = {"n4"}

    result = run_e1_decoy_trust_decay(
        profiles, query_vectors, relevant_nodes, coarse_k=4, top_k=1, m=3, seed=0
    )

    assert result["n_queries"] == len(queries)
    assert result["decoy_heavy_node_count"] + result["genuine_heavy_node_count"] <= len(profiles)
    for key in ("a2_leakage_first_half", "a2_leakage_second_half"):
        value = result[key]
        assert value != value or 0.0 <= value <= 1.0  # nan or valid fraction
