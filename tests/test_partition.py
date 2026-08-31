import numpy as np

from data.partition import partition_by_cluster, partition_corpus, partition_random


def test_partition_random_covers_every_document_exactly_once():
    rng = np.random.default_rng(0)
    groups = partition_random(20, 4, rng)
    all_indices = sorted(i for group in groups for i in group)
    assert all_indices == list(range(20))


def test_partition_by_cluster_covers_every_document_exactly_once():
    rng = np.random.default_rng(0)
    embeddings = rng.normal(size=(20, 3))
    groups = partition_by_cluster(embeddings, 4, rng)
    all_indices = sorted(i for group in groups for i in group)
    assert all_indices == list(range(20))


def test_partition_corpus_rejects_unknown_strategy():
    import pytest

    rng = np.random.default_rng(0)
    embeddings = rng.normal(size=(5, 2))
    with pytest.raises(ValueError):
        partition_corpus(embeddings, 2, rng, strategy="bogus")
