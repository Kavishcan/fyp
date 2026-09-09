"""Development-tunable, same-information source-fusion controls, not RAGRoute."""
from __future__ import annotations

import math

from router.evidence_budget import AllocationConfig, allocate, prepare_profiles
from router.lexical_profile import fuse_scores, lexical_scores


def fusion_scores(semantic, lexical, method, weight, constant=60):
    if isinstance(weight, bool) or not math.isfinite(weight) or not 0 <= weight <= 1:
        raise ValueError("weight must be finite and in [0,1]")
    if method not in {"weighted_rrf", "minmax"}:
        raise ValueError("unknown fusion control")
    if isinstance(constant, bool) or not math.isfinite(constant) or constant <= 0:
        raise ValueError("RRF constant must be positive and finite")
    if lexical is None or not semantic:
        return semantic.copy()
    if set(semantic) != set(lexical):
        raise ValueError("source sets differ")
    if any(not math.isfinite(v) for scores in (semantic, lexical) for v in scores.values()):
        raise ValueError("nonfinite score")
    # Keep endpoint tie behavior identical to the semantic and lexical controls.
    if weight == 0:
        return semantic.copy()
    if weight == 1:
        return fuse_scores(semantic, lexical, "lexical")
    if method == "weighted_rrf":
        ranks = [{s: i + 1 for i, s in enumerate(sorted(scores, key=lambda s: (-scores[s], s)))}
                 for scores in (semantic, lexical)]
        return {s: (1 - weight) / (constant + ranks[0][s]) + weight / (constant + ranks[1][s])
                for s in semantic}

    def scale(scores):
        lo, hi = min(scores.values()), max(scores.values())
        return {s: (v - lo) / (hi - lo) if hi > lo else 0. for s, v in scores.items()}

    a, b = scale(semantic), scale(lexical)
    return {s: (1 - weight) * a[s] + weight * b[s] for s in semantic}


def run_control(query, question, profiles, retrieve, method, weight=.25, constant=60):
    """Select using cached profiles; retrieve only the selected sources, C=3/B=12."""
    if method in {"semantic16", "semantic21", "hybrid", "lexical", "rrf"}:
        strategy = "semantic" if method.startswith("semantic") else method
        return allocate(query, profiles, retrieve,
                        AllocationConfig(3, 12, 5, "equal", profile_strategy=strategy, lexical_weight=weight),
                        question=question)
    _, _, semantic, _, _ = prepare_profiles(query, profiles)
    eligible = [p for p in profiles if p.source_id in semantic]
    lexical = lexical_scores(question, eligible)
    scores = fusion_scores(semantic, lexical, method, weight, constant)
    selected = sorted(scores, key=lambda s: (-scores[s], s))[:3]
    # Every selected source has positive semantic relevance. Passing this subset
    # to the existing equal allocator preserves charging, paging and final ranking.
    return allocate(query, [p for p in eligible if p.source_id in selected], retrieve,
                    AllocationConfig(3, 12, 5, "equal"))
