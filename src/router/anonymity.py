"""Anonymity-set construction (docs/04-router-design.md section 7).

The router constructs the genuine and decoy lists itself, so this module does
not hide that distinction from the router — it is evaluated against the
separate A2 routing observer, not against the router's own state.

Two decoy-sampling strategies are provided so they can be compared directly
under repeated-query intersection, per the design requirements: a plain random
sample, and a topic-stable sample that returns the same cover set for the same
topic every time. Without topic stability, an observer who sees the same query
topic repeatedly can intersect the dispatched sets across queries and recover
the genuine sources by elimination — the random variant exists to demonstrate
that failure, not as a competitive alternative.
"""
from __future__ import annotations

import hashlib
import random


def random_sample(pool: list[str], count: int, rng: random.Random) -> list[str]:
    count = max(0, min(count, len(pool)))
    return rng.sample(pool, count)


def topic_stable_sample(pool: list[str], count: int, topic_key: str) -> list[str]:
    """Deterministic sample keyed on `topic_key`, stable across repeated calls
    with the same topic and pool. Uses a stable hash rather than a seeded RNG
    so results depend only on (topic_key, pool membership), not call order.
    """
    count = max(0, min(count, len(pool)))
    if count == 0:
        return []

    def rank_key(source_id: str) -> str:
        return hashlib.sha256(f"{topic_key}:{source_id}".encode("utf-8")).hexdigest()

    return sorted(pool, key=rank_key)[:count]


def add_decoys(
    real: list[str],
    candidates: list[str],
    m: int,
    *,
    topic_key: str | None = None,
    rng: random.Random | None = None,
) -> list[str]:
    """Pad `real` with decoys drawn from `candidates` up to total size `m`.

    Decoys are sampled from the coarse candidate pool, not the full source
    catalogue, so every dispatched source is at least plausibly relevant
    (docs/04-router-design.md section 7). Pass `topic_key` for the topic-stable
    strategy (recommended); pass `rng` instead for the random baseline used to
    demonstrate why topic stability matters.
    """
    if topic_key is None and rng is None:
        raise ValueError("add_decoys requires either topic_key or rng")
    pool = [s for s in candidates if s not in real]
    needed = max(0, m - len(real))
    if topic_key is not None:
        decoys = topic_stable_sample(pool, needed, topic_key)
    else:
        decoys = random_sample(pool, needed, rng)
    dispatched = list(real) + decoys
    # Shuffle order must not correlate with real/decoy identity (design
    # requirement). Uses a fresh RNG rather than one derived from topic_key so
    # dispatch order does not itself become a stable, observable fingerprint.
    (rng or random.Random()).shuffle(dispatched)
    return dispatched
