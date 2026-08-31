import numpy as np
import pytest

from nodes.profile import bucket_document_count, redact_pii
from nodes.simulator import InProcessNode, build_simulated_source, forge_profile


def toy_embedder(texts):
    """Deterministic 2D embedding: [count of 'cat', count of 'dog']."""
    return np.array(
        [[t.lower().count("cat"), t.lower().count("dog")] for t in texts], dtype=np.float64
    )


def other_toy_embedder(texts):
    """A second, unrelated 2D space: [count of 'bird', count of 'fish'].
    Stands in for "a different node's local embedding model."
    """
    return np.array(
        [[t.lower().count("bird"), t.lower().count("fish")] for t in texts], dtype=np.float64
    )


def test_redact_pii_removes_email_and_ssn_like_patterns():
    text = "Contact jane.doe@example.com, SSN 123-45-6789."
    redacted = redact_pii(text)
    assert "example.com" not in redacted
    assert "123-45-6789" not in redacted


def test_bucket_document_count_boundaries():
    assert bucket_document_count(0) == "0"
    assert bucket_document_count(50) == "1-100"
    assert bucket_document_count(500) == "101-1000"
    assert bucket_document_count(200_000) == "100000+"


def test_build_simulated_source_produces_node_and_profile():
    documents = ["a cat sat", "a dog ran", "cat and dog play", "just a cat"]
    node, profile = build_simulated_source(
        "source-1",
        documents,
        toy_embedder,
        k=2,
        sigma=0.0,
        rng=np.random.default_rng(0),
    )
    assert node.source_id == "source-1"
    assert profile.source_id == "source-1"
    assert profile.centroids.shape[1] == 2
    assert profile.document_count_bucket == "1-100"


def test_in_process_node_retrieve_ranks_matching_document_first():
    documents = ["a cat sat", "a dog ran", "nothing relevant here"]
    node, _ = build_simulated_source(
        "source-1", documents, toy_embedder, k=1, sigma=0.0, rng=np.random.default_rng(0)
    )
    results = node.retrieve(np.array([1.0, 0.0]), top_n=1)
    assert results[0].document == "a cat sat"


def test_build_simulated_source_defaults_local_embedder_to_routing_embedder():
    documents = ["a cat sat"]
    node, profile = build_simulated_source(
        "source-1", documents, toy_embedder, k=1, sigma=0.0, rng=np.random.default_rng(0)
    )
    assert node.local_embedder is toy_embedder
    # Same embedder for both, so the node's own index equals what routing used.
    np.testing.assert_array_equal(node.document_embeddings, toy_embedder(documents))


def test_heterogeneous_embedders_keep_routing_and_local_spaces_separate():
    documents = ["a cat and a bird", "a dog and a fish"]
    node, profile = build_simulated_source(
        "source-1",
        documents,
        toy_embedder,  # routing space: cat/dog
        other_toy_embedder,  # local space: bird/fish
        k=1,
        sigma=0.0,
        rng=np.random.default_rng(0),
    )
    # Profile centroids came from the routing embedder (cat/dog space): with
    # k=1 the single centroid is the mean of the routing-space embeddings.
    assert profile.centroids.shape[1] == 2
    expected_centroid = toy_embedder(documents).mean(axis=0)
    np.testing.assert_array_almost_equal(profile.centroids[0], expected_centroid)
    # The node's own index came from its local embedder (bird/fish space), not
    # from the routing embedder — this is the whole point of the split.
    np.testing.assert_array_equal(node.document_embeddings, other_toy_embedder(documents))


def test_retrieve_from_text_uses_the_nodes_own_local_embedder():
    documents = ["a bird flew by", "a fish swam past", "nothing relevant"]
    node, _ = build_simulated_source(
        "source-1",
        documents,
        toy_embedder,  # routing space would score everything zero here
        other_toy_embedder,  # local space actually distinguishes these docs
        k=1,
        sigma=0.0,
        rng=np.random.default_rng(0),
    )
    results = node.retrieve_from_text("looking for a bird", top_n=1)
    assert results[0].document == "a bird flew by"


def test_retrieve_from_text_raises_clearly_without_a_local_embedder():
    node = InProcessNode("source-1", ["doc"], np.array([[1.0, 0.0]]), local_embedder=None)
    with pytest.raises(ValueError, match="local_embedder"):
        node.retrieve_from_text("query")


def test_forge_profile_replaces_centroids_but_keeps_source_id():
    documents = ["a cat sat"]
    _, profile = build_simulated_source(
        "attacker", documents, toy_embedder, k=1, sigma=0.0, rng=np.random.default_rng(0)
    )
    forged = forge_profile(profile, target_centroids=np.array([[0.0, 5.0]]))
    assert forged.source_id == "attacker"
    assert forged.profile_version == profile.profile_version + 1
    assert np.array_equal(forged.centroids, np.array([[0.0, 5.0]]))
