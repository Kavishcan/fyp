import numpy as np

from api.embedder import HashingEmbedder


def test_same_model_name_is_deterministic():
    a = HashingEmbedder(model_name="toy-e5")
    b = HashingEmbedder(model_name="toy-e5")
    np.testing.assert_array_equal(a.embed(["chemo protocol"]), b.embed(["chemo protocol"]))


def test_different_model_names_produce_different_spaces():
    a = HashingEmbedder(model_name="toy-e5")
    b = HashingEmbedder(model_name="toy-bge")
    va = a.embed(["chemo protocol for tumour"])[0]
    vb = b.embed(["chemo protocol for tumour"])[0]
    assert not np.array_equal(va, vb)


def test_default_model_name_is_the_shared_routing_model():
    from api.embedder import SHARED_ROUTING_MODEL

    e = HashingEmbedder()
    assert e.model_name == SHARED_ROUTING_MODEL
