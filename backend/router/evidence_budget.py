"""Experimental candidate-level allocation; no relevance labels or trust learning.

Retrieval is a charged, one-passage action. The callback must return only the
requested page, never an uncharged preview of the rest of the local ranking.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
import time
from typing import Callable

import numpy as np

from baselines.base import SourceProfile

METHODS = ("equal", "proportional", "profile_only", "allocation_only", "joint")


@dataclass(frozen=True)
class AllocationConfig:
    max_sources: int = 3
    candidate_budget: int = 12
    final_k: int = 5
    method: str = "joint"

    def __post_init__(self):
        for name in ("max_sources", "candidate_budget", "final_k"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        if self.method not in METHODS:
            raise ValueError(f"method must be one of {METHODS}")


@dataclass
class Candidate:
    source_id: str
    document_id: str
    document: str
    embedding: np.ndarray


@dataclass
class AllocationResult:
    config: AllocationConfig
    contacted: list[str] = field(default_factory=list)
    quotas: dict[str, int] = field(default_factory=dict)
    candidates: list[Candidate] = field(default_factory=list)
    final: list[Candidate] = field(default_factory=list)
    actions: list[dict] = field(default_factory=list)
    skipped_profiles: dict[str, str] = field(default_factory=dict)
    stop_reason: str = "candidate_budget"
    elapsed_ms: float = 0.0

    def to_dict(self):
        return dict(config=asdict(self.config), contacted=self.contacted, quotas=self.quotas,
                    requests=len(self.actions), candidate_slots_spent=len(self.actions),
                    returned=sum(a["returned"] for a in self.actions),
                    unique_candidates=len(self.candidates),
                    text_bytes_received=sum(a["text_bytes"] for a in self.actions),
                    duplicates=sum(a["duplicate"] for a in self.actions),
                    actions=self.actions, skipped_profiles=self.skipped_profiles,
                    final_document_ids=[p.document_id for p in self.final],
                    stop_reason=self.stop_reason, elapsed_ms=self.elapsed_ms)


def unit_rows(values):
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 2 or not np.isfinite(values).all():
        raise ValueError("expected a finite matrix")
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    return np.divide(values, norms, out=np.zeros_like(values), where=norms > 0)


def prepare_profiles(query, profiles):
    query = np.asarray(query, dtype=np.float64)
    if query.ndim != 1 or not len(query) or not np.isfinite(query).all():
        raise ValueError("expected a finite query vector")
    q = unit_rows(query[None])[0]
    matrices, relevance, weights, skipped = {}, {}, {}, {}
    seen = set()
    for p in sorted(profiles, key=lambda p: p.source_id):
        sid = p.source_id
        if sid in seen:
            raise ValueError("duplicate source_id")
        seen.add(sid)
        try:
            c = unit_rows(p.centroids)
            if not len(c) or c.shape[1] != len(q):
                raise ValueError("profile dimension mismatch or empty profile")
            similarities = np.clip(c @ q, 0, 1)
            r = float(similarities.max())
            if r == 0:
                skipped[sid] = "no_positive_profile_relevance"
                continue
            matrices[sid], relevance[sid] = c, r
            weights[sid] = similarities ** 2 / float(np.sum(similarities ** 2))
        except (ValueError, TypeError):
            skipped[sid] = "invalid_profile"
    return q, matrices, relevance, weights, skipped


def fixed_quotas(relevance, config):
    """One guaranteed slot per top source, then uniform or Hamilton remainder."""
    selected = sorted(relevance, key=lambda s: (-relevance[s], s))[
        :min(config.max_sources, config.candidate_budget)]
    if not selected:
        return {}
    quotas = dict.fromkeys(selected, 1)
    remaining = config.candidate_budget - len(selected)
    weights = np.array([relevance[s] if config.method == "proportional" else 1 for s in selected])
    shares = remaining * weights / weights.sum()
    floors = np.floor(shares).astype(int)
    for sid, n in zip(selected, floors):
        quotas[sid] += int(n)
    order = sorted(range(len(selected)), key=lambda i: (-(shares[i] - floors[i]), i))
    for i in order[:remaining - int(floors.sum())]:
        quotas[selected[i]] += 1
    return quotas


def allocate(query, profiles: list[SourceProfile], retrieve: Callable[[str, int], Candidate | None],
             config=AllocationConfig()) -> AllocationResult:
    """Choose (source, next local rank) actions from profiles and observed text.

    Profiles must already be authorization-filtered by the coordinator. Returned
    embeddings must use its routing encoder, not incomparable remote scores.
    """
    start = time.perf_counter()
    result = AllocationResult(config)
    q, matrices, relevance, weights, result.skipped_profiles = prepare_profiles(query, profiles)
    fixed = fixed_quotas(relevance, config)
    eligible = set(fixed) if config.method in {"equal", "proportional", "allocation_only"} else set(relevance)
    coverage = {sid: np.zeros(len(c)) for sid, c in matrices.items()}
    last = relevance.copy()
    blocked, seen = set(), set()
    for _ in range(config.candidate_budget):
        choices = {}
        for sid in sorted(eligible - blocked):
            n = result.quotas.get(sid, 0)
            if n == 0 and len(result.contacted) >= config.max_sources:
                continue
            if config.method in {"equal", "proportional"}:
                if n < fixed[sid]:
                    # Round-robin execution of a fixed plan, no feedback adaptation.
                    choices[sid] = (fixed[sid] - n) / fixed[sid]
            else:
                residual = float(weights[sid] @ (1 - coverage[sid]))
                quality = (relevance[sid] + last[sid]) / 2
                if config.method == "profile_only":
                    residual, quality = 1., relevance[sid]
                choices[sid] = quality * residual / math.sqrt(n + 1)
        if not choices:
            result.stop_reason = "no_eligible_actions"
            break
        sid = min(choices, key=lambda s: (-choices[s], -relevance[s], s))
        offset = result.quotas.get(sid, 0)
        # Charge before IO. Failure/empty/duplicate never refunds a slot.
        if offset == 0:
            result.contacted.append(sid)
        result.quotas[sid] = offset + 1
        action = dict(source_id=sid, offset=offset, estimated_gain=choices[sid],
                      returned=0, duplicate=0, text_bytes=0, error=None)
        tick = time.perf_counter()
        try:
            passage = retrieve(sid, offset)
            if passage is None:
                blocked.add(sid)
            else:
                action["returned"] = 1
                action["text_bytes"] = len(passage.document.encode("utf-8"))
                if passage.source_id != sid or not passage.document_id or not passage.document.strip():
                    raise ValueError("invalid candidate identity or empty text")
                v = unit_rows(np.asarray(passage.embedding)[None])[0]
                if len(v) != len(q):
                    raise ValueError("candidate embedding dimension mismatch")
                last[sid] = float(np.clip(q @ v, 0, 1))
                action["document_id"] = passage.document_id
                action["query_relevance"] = last[sid]
                action["duplicate"] = int(passage.document_id in seen)
                if not action["duplicate"]:
                    seen.add(passage.document_id)
                    result.candidates.append(passage)
                    for source, c in matrices.items():
                        coverage[source] = np.maximum(coverage[source], np.clip(c @ v, 0, 1) ** 2)
        except Exception as exc:
            action["error"] = type(exc).__name__
            blocked.add(sid)
        action["retrieval_ms"] = (time.perf_counter() - tick) * 1000
        result.actions.append(action)
    ranked = sorted(result.candidates, key=lambda p: (
        -float(unit_rows(np.asarray(p.embedding)[None])[0] @ q), p.document_id, p.source_id))
    result.final = ranked[:config.final_k]
    result.elapsed_ms = (time.perf_counter() - start) * 1000
    return result
