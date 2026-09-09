"""Compact lexical-presence profiles. Hashing is NOT a privacy guarantee."""
from __future__ import annotations

import base64
import hashlib
import re
from functools import lru_cache

import numpy as np

from nodes.metadata import _STOP

BITS = 65536
BYTES = BITS // 8
VERSION = "sha256-unigram-presence-65536-v1"
TOKENS = re.compile(r"(?u)\b\w{2,}\b")


def buckets(text):
    terms = set(TOKENS.findall(text.casefold())) - _STOP
    return {int.from_bytes(hashlib.sha256(t.encode("utf-8")).digest()[:2], "big")
            for t in terms if not t.isdecimal()}


def build_sketch(documents):
    bits = np.zeros(BITS, dtype=np.uint8)
    for text in documents:
        indices = list(buckets(text))
        bits[indices] = 1
    return base64.b64encode(np.packbits(bits).tobytes()).decode("ascii")


@lru_cache(maxsize=1024)
def decode_sketch(value):
    raw = base64.b64decode(value, validate=True)
    if len(raw) != BYTES:
        raise ValueError("invalid lexical sketch length")
    bits = np.unpackbits(np.frombuffer(raw, dtype=np.uint8))
    bits.setflags(write=False)
    return bits


def lexical_scores(question, profiles):
    """Source-IDF weighted presence; ignore universally present/absent buckets.

    All eligible profiles must use the same representation. Missing or invalid
    metadata falls back for the whole query, never penalizes one absent source.
    """
    indices = sorted(buckets(question))
    if not profiles or not indices:
        return None
    try:
        if any(p.lexical_version != VERSION or not p.lexical_sketch for p in profiles):
            return None
        present = np.stack([decode_sketch(p.lexical_sketch)[indices] for p in profiles])
    except (ValueError, TypeError):
        return None
    df = present.sum(axis=0)
    useful = (df > 0) & (df < len(profiles))
    if not useful.any():
        return None
    w = np.log((len(profiles) + 1) / (df[useful] + 1)) ** 2
    scores = present[:, useful] @ w / w.sum()
    return {p.source_id: float(s) for p, s in zip(profiles, scores)}


def fuse_scores(semantic, lexical, strategy, weight=.5):
    if lexical is None or strategy == "semantic":
        return semantic.copy()
    if set(semantic) != set(lexical):
        raise ValueError("lexical and semantic source sets must match")
    if strategy == "lexical":
        # Semantic score is only a deterministic tie break, not an extra signal.
        order = sorted(semantic, key=lambda s: (-lexical[s], -semantic[s], s))
        return {s: (len(order) - rank) / len(order) for rank, s in enumerate(order)}
    if strategy == "hybrid":
        if weight == 1:
            return fuse_scores(semantic, lexical, "lexical")
        return {s: (1 - weight) * semantic[s] + weight * lexical[s] for s in semantic}
    if strategy == "rrf":
        ranks = [{s: i + 1 for i, s in enumerate(sorted(scores, key=lambda s: (-scores[s], s)))}
                 for scores in (semantic, lexical)]
        return {s: .5 * (61 / (60 + ranks[0][s]) + 61 / (60 + ranks[1][s])) for s in semantic}
    raise ValueError("unknown profile strategy")
