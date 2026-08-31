"""A2: source inference — the project's primary new measurement.

An observer sees which sources are contacted for queries of a given topic,
across many queries, but never the query content or which contacted sources
were genuine versus decoys. This is a frequency/co-occurrence adversary: a
source that appears in nearly every dispatch for a topic is a strong genuine
candidate; one that appears inconsistently looks like a decoy. This is
exactly the failure mode topic-stable decoys (router/anonymity.py) are
designed to resist, and exactly what random decoys fail to resist — comparing
this attack's accuracy under both decoy strategies is the core experiment.
"""
from __future__ import annotations

from collections import defaultdict


class SourceInferenceObserver:
    def __init__(self) -> None:
        self._counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._topic_queries: dict[str, int] = defaultdict(int)

    def observe(self, topic_key: str, dispatched_source_ids: list[str]) -> None:
        self._topic_queries[topic_key] += 1
        for source_id in dispatched_source_ids:
            self._counts[topic_key][source_id] += 1

    def infer_topic_sources(self, topic_key: str, top_n: int) -> list[str]:
        """Best-first guess at which sources genuinely serve `topic_key`,
        ranked by how consistently they appear across observed queries for
        that topic.
        """
        counts = self._counts.get(topic_key, {})
        ranked = sorted(counts, key=counts.get, reverse=True)
        return ranked[:top_n]

    def appearance_frequency(self, topic_key: str, source_id: str) -> float:
        total = self._topic_queries.get(topic_key, 0)
        if total == 0:
            return 0.0
        return self._counts.get(topic_key, {}).get(source_id, 0) / total


class IntersectionObserver:
    """A sharper A2 variant: intersect the dispatched sets observed for the
    same topic across repeated queries. If decoys vary query to query, the
    intersection shrinks toward exactly the genuine set. If decoys are
    topic-stable (the same cover set every time), the intersection never
    shrinks past the full dispatched set, because the decoys are also
    constant — this is precisely the vulnerability topic-stable sampling is
    designed to close (router/anonymity.py module docstring).
    """

    def __init__(self) -> None:
        self._running_intersection: dict[str, set] = {}

    def observe(self, topic_key: str, dispatched_source_ids: list[str]) -> None:
        dispatched = set(dispatched_source_ids)
        if topic_key not in self._running_intersection:
            self._running_intersection[topic_key] = dispatched
        else:
            self._running_intersection[topic_key] &= dispatched

    def current_estimate(self, topic_key: str) -> set:
        return set(self._running_intersection.get(topic_key, set()))


def inference_accuracy(
    observer: SourceInferenceObserver,
    ground_truth: dict[str, set],
) -> dict[str, float]:
    """For each topic, precision of the observer's top-|genuine| guess against
    the true genuine set. Returns per-topic accuracy plus a 'mean' key.
    """
    per_topic: dict[str, float] = {}
    for topic_key, genuine in ground_truth.items():
        if not genuine:
            continue
        guess = set(observer.infer_topic_sources(topic_key, len(genuine)))
        per_topic[topic_key] = len(guess & genuine) / len(genuine)
    per_topic["mean"] = sum(v for k, v in per_topic.items() if k != "mean") / max(len(per_topic), 1)
    return per_topic
