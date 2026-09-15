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


# --- fixed anonymity cells (docs/40) -----------------------------------------
#
# docs/39 showed that a cover set chosen per topic is itself a topic
# fingerprint, and a random cover set exposes the genuine source through
# intersection. A cover set that is a FIXED function of the genuine source —
# the same cell of sources, every time, for every query that lands on any
# member of that cell — is stable (nothing to intersect away) and, if cells
# are built to span domains, not a function of the topic (nothing to learn
# beyond the cell). The observer learns the cell; the cell spans topics.


def build_cells(source_ids: list[str], group_of: dict[str, str], cell_size: int) -> list[list[str]]:
    """Partition sources into cells of `cell_size`, each as domain-diverse as
    the population allows: sources are dealt round-robin across groups so
    consecutive cells draw from different groups. Deterministic given the
    inputs. A short final cell is merged into the previous one."""
    if cell_size < 1:
        raise ValueError("cell_size must be positive")
    by_group: dict[str, list[str]] = {}
    for sid in sorted(source_ids):
        by_group.setdefault(group_of.get(sid, "?"), []).append(sid)
    order: list[str] = []
    queues = [by_group[g] for g in sorted(by_group)]
    while any(queues):
        for queue in queues:
            if queue:
                order.append(queue.pop(0))
    cells = [order[i:i + cell_size] for i in range(0, len(order), cell_size)]
    if len(cells) > 1 and len(cells[-1]) < cell_size:
        cells[-2].extend(cells.pop())
    return cells


def cell_cover(genuine: list[str], cells: list[list[str]], max_sources: int) -> list[str]:
    """Dispatch set = union of the cells containing the genuine sources, in
    genuine order, until adding the next whole cell would exceed
    `max_sources`. A genuine source whose cell does not fit is dropped rather
    than contacted alone — contacting it outside its cell would expose it."""
    cell_of = {sid: tuple(cell) for cell in cells for sid in cell}
    dispatched: list[str] = []
    seen: set[tuple[str, ...]] = set()
    for sid in genuine:
        cell = cell_of.get(sid)
        if cell is None or cell in seen:
            continue
        if len(dispatched) + len(cell) > max_sources:
            continue
        seen.add(cell)
        dispatched.extend(cell)
    return dispatched
