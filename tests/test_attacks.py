import random

import numpy as np
import pytest

from attacks.a1_inversion import NearestNeighbourInversion, term_recovery_rate
from attacks.a2_source_inference import IntersectionObserver, SourceInferenceObserver
from router.anonymity import add_decoys


def test_nearest_neighbour_inversion_recovers_closest_reference_text():
    reference_texts = ["diabetes treatment options", "car engine repair guide"]
    reference_embeddings = np.array([[1.0, 0.0], [0.0, 1.0]])
    attack = NearestNeighbourInversion(reference_texts, reference_embeddings)
    recovered = attack.recover(np.array([0.9, 0.1]))
    assert recovered == "diabetes treatment options"


def test_term_recovery_rate_is_one_for_identical_text():
    assert term_recovery_rate("insulin dosage query", "insulin dosage query") == pytest.approx(1.0)


def test_term_recovery_rate_is_zero_for_disjoint_text():
    assert term_recovery_rate("insulin dosage", "car engine repair") == 0.0


def test_source_inference_observer_identifies_consistently_appearing_source():
    observer = SourceInferenceObserver()
    for _ in range(20):
        observer.observe("oncology", ["real", "decoy_a", "decoy_b"])
    top = observer.infer_topic_sources("oncology", top_n=1)
    assert top == ["real"]


def test_random_decoys_let_intersection_attack_converge_on_genuine_sources():
    """Without topic stability, an observer intersecting dispatched sets
    across repeated same-topic queries watches the intersection shrink toward
    exactly the genuine set, because the decoys are different every time.
    """
    real = {"real1", "real2"}
    candidates = list(real) + [f"decoy{i}" for i in range(30)]
    rng = random.Random(0)
    observer = IntersectionObserver()
    for _ in range(15):
        dispatched = add_decoys(list(real), candidates, m=8, rng=rng)
        observer.observe("oncology", dispatched)
    assert observer.current_estimate("oncology") == real


def test_topic_stable_decoys_prevent_the_intersection_attack_from_converging():
    """With topic-stable decoys, the same cover set is dispatched every time,
    so the intersection never shrinks past the full dispatched set — the
    observer cannot isolate the genuine sources from their stable decoys.
    """
    real = {"real1", "real2"}
    candidates = list(real) + [f"decoy{i}" for i in range(30)]
    observer = IntersectionObserver()
    for _ in range(15):
        dispatched = add_decoys(list(real), candidates, m=8, topic_key="oncology")
        observer.observe("oncology", dispatched)
    estimate = observer.current_estimate("oncology")
    assert real.issubset(estimate)
    assert len(estimate) == 8  # never shrank below the full dispatched set size
