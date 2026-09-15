"""A2-reverse: query-topic inference from the contacted-source set (docs/39).

attacks/a2_source_inference.py asks "given a topic, which sources are
genuine?" The original research concern runs the other way: an observer
who sees ONLY which sources were contacted for one query — never its text,
vector, or which contacts were decoys — tries to name the query's topic.
Repeated over many queries this is what makes a dispatch pattern a leak.

Two attackers, so routing leakage can be separated from what is already
public:

- `SetPriorAttacker` (metadata / chance floor): knows each source's public
  domain label (from its published profile or engine description) and
  nothing else. It guesses the topic of a contacted source at random. Its
  accuracy is 1/|contacted set| when the genuine source is in the set — the
  anonymity the decoys nominally provide.
- `HistoryAttacker` (learned observer): has seen a labelled history of
  (contacted set, topic) pairs — an insider, or an observer who later
  learned topics for a fraction of past queries — and predicts with a
  multinomial naive-Bayes model over the multi-hot contact vector. This is
  the attacker topic-stable decoys must resist: if the same topic always
  produces the same cover set, the cover set IS the topic.

Metrics per condition: accuracy, macro-F1, top-3 accuracy, and the same
figures for the chance floor 1/|topics|.

No cryptography is involved; the attack works purely on identities. It
therefore applies unchanged to psi mode, whose dispatch pattern is v2's.
"""
from __future__ import annotations

import math
import random
from collections import Counter, defaultdict


def macro_f1(y_true: list[str], y_pred: list[str], labels: list[str]) -> float:
    scores = []
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
        if tp == 0 and (fp or fn):
            scores.append(0.0)
        elif tp == 0:
            continue  # label absent from both; skip rather than reward
        else:
            precision, recall = tp / (tp + fp), tp / (tp + fn)
            scores.append(2 * precision * recall / (precision + recall))
    return sum(scores) / len(scores) if scores else 0.0


class SetPriorAttacker:
    """Metadata-only floor: pick a contacted source's domain at random."""

    def __init__(self, source_topic: dict[str, str], seed: int = 0) -> None:
        self.source_topic = source_topic
        self._rng = random.Random(seed)

    def rank(self, contacted: list[str]) -> list[str]:
        topics = list(dict.fromkeys(self.source_topic[s] for s in contacted if s in self.source_topic))
        self._rng.shuffle(topics)
        return topics


class HistoryAttacker:
    """Multinomial naive Bayes over multi-hot contact vectors, with Laplace
    smoothing. Trained on a labelled history; ranks topics for a new set."""

    def __init__(self, alpha: float = 1.0) -> None:
        self.alpha = alpha
        self._topic_count: Counter = Counter()
        self._source_given_topic: dict[str, Counter] = defaultdict(Counter)
        self._sources: set[str] = set()

    def fit(self, history: list[tuple[list[str], str]]) -> "HistoryAttacker":
        for contacted, topic in history:
            self._topic_count[topic] += 1
            for s in contacted:
                self._source_given_topic[topic][s] += 1
                self._sources.add(s)
        return self

    @property
    def topics(self) -> list[str]:
        return sorted(self._topic_count)

    def rank(self, contacted: list[str]) -> list[str]:
        total = sum(self._topic_count.values())
        contacted_set = set(contacted)
        scores = {}
        for topic, n in self._topic_count.items():
            log_p = math.log(n / total)
            for s in self._sources:
                p = (self._source_given_topic[topic][s] + self.alpha) / (n + 2 * self.alpha)
                log_p += math.log(p if s in contacted_set else 1.0 - p)
            scores[topic] = log_p
        return sorted(scores, key=scores.get, reverse=True)


def evaluate(attacker, cases: list[tuple[list[str], str]], labels: list[str], top_k: int = 3) -> dict:
    y_true, y_pred, hits_k = [], [], []
    for contacted, topic in cases:
        ranking = attacker.rank(contacted)
        y_true.append(topic)
        y_pred.append(ranking[0] if ranking else "")
        hits_k.append(1.0 if topic in ranking[:top_k] else 0.0)
    n = len(cases)
    return {
        "accuracy": sum(1 for t, p in zip(y_true, y_pred) if t == p) / n if n else float("nan"),
        "macro_f1": macro_f1(y_true, y_pred, labels),
        f"top{top_k}_accuracy": sum(hits_k) / n if n else float("nan"),
        "chance": 1.0 / len(labels) if labels else float("nan"),
        "cases": n,
    }


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a | b) else 1.0
