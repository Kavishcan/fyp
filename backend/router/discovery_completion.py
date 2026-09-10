"""Experimental budgeted acquisition; query-term deficits are not evidence labels."""
from dataclasses import dataclass
import re

import numpy as np

from nodes.metadata import _STOP


def terms(text):
    return set(re.findall(r"\b\w+\b", text.casefold())) - _STOP


@dataclass(frozen=True)
class Passage:
    source_id: str
    chunk_id: str
    parent_id: str
    text: str
    embedding: np.ndarray


def acquire(question, query, source_priors, retrieve, *, budget=12, final_k=5,
            completion=True):
    """retrieve(source, parent_or_none, seen_chunks, seen_parents) -> Passage|None.

    None parent means discover an unseen parent. Failed calls consume budget.
    Caller supplies an already contact-capped, authorized source selection.
    """
    for value in (budget, final_k):
        if type(value) is not int or value < 0:
            raise ValueError("budgets must be nonnegative integers")
    q = np.asarray(query, dtype=float)
    if q.ndim != 1 or not np.isfinite(q).all() or np.linalg.norm(q) == 0:
        raise ValueError("query must be finite and nonzero")
    q = q / np.linalg.norm(q)
    if any(not np.isfinite(v) or not 0 <= v <= 1 for v in source_priors.values()):
        raise ValueError("source priors must be in [0,1]")
    sources = sorted(source_priors, key=lambda s: (-source_priors[s], s))
    seen, parents, scores, texts = set(), {}, {}, {}
    counts, observed, closed, actions, passages = {}, {}, set(), [], []
    query_terms = terms(question)
    while len(actions) < budget:
        priorities = {}
        seed = next((s for s in sources if (s, None) not in counts), None)
        for s in sources:
            arm = (s, None)
            if arm not in closed:
                n = counts.get(arm, 0)
                priorities[arm] = (source_priors[s] + observed.get(s, 0.)) / (1+n)**2
        if completion and len(parents) >= min(final_k, budget):
            for arm in parents:
                if arm not in closed:
                    deficit = len(query_terms - texts[arm]) / max(1, len(query_terms))
                    priorities[arm] = scores[arm] * deficit / (1 + counts.get(arm, 0))
        if not priorities:
            break
        arm = (seed, None) if seed is not None else min(
            priorities, key=lambda a: (-priorities[a], a[0], a[1] or ""))
        sid, parent = arm
        counts[arm] = counts.get(arm, 0) + 1
        action = dict(source=sid, parent=parent, kind="discover" if parent is None else "complete",
                      priority=priorities[arm], status="empty")
        actions.append(action)
        try:
            p = retrieve(sid, parent, frozenset(c for s,c in seen if s == sid),
                         frozenset(d for s,d in parents if s == sid))
            if p is None:
                closed.add(arm)
                continue
            v = np.asarray(p.embedding, dtype=float)
            key = (sid, p.chunk_id)
            if (p.source_id != sid or not p.chunk_id or not p.parent_id or key in seen
                    or (parent is not None and p.parent_id != parent)
                    or (parent is None and (sid, p.parent_id) in parents)
                    or v.shape != q.shape or not np.isfinite(v).all() or np.linalg.norm(v) == 0):
                raise ValueError("invalid acquisition response")
            similarity = float(np.clip(q @ v / np.linalg.norm(v), 0, 1))
        except Exception as exc:
            action.update(status="error", error=type(exc).__name__)
            closed.add(arm)
            continue
        seen.add(key)
        pk = (sid, p.parent_id)
        parents[pk] = True
        scores[pk] = max(scores.get(pk, 0.), similarity)
        texts.setdefault(pk, set()).update(terms(p.text))
        if parent is None:
            observed[sid] = observed.get(sid, 0.) + similarity
        passages.append(p)
        action.update(status="ok", chunk=p.chunk_id, returned_parent=p.parent_id, similarity=similarity)
    ranked = sorted(passages, key=lambda p: (
        -float(q @ p.embedding / np.linalg.norm(p.embedding)), p.chunk_id, p.source_id))
    return dict(candidates=passages, final=ranked[:final_k], actions=actions)


def select_local(order, parents, parent, seen_chunks, seen_parents):
    """Node-local action executor. IDs in order are opaque chunk IDs."""
    for chunk in order:
        if chunk in seen_chunks:
            continue
        if (parent is None and parents[chunk] not in seen_parents) or parents[chunk] == parent:
            return chunk
    return None
