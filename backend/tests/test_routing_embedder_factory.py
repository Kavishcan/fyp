"""ROUTING_EMBEDDER selects the one shared routing space for coordinator and nodes."""
from __future__ import annotations

import json

from api.state import AppState
from nodes.embedding import HashingEmbedder, SHARED_ROUTING_MODEL, routing_embedder_name, shared_routing_embedder


def test_default_is_the_hashing_placeholder(monkeypatch):
    monkeypatch.delenv("ROUTING_EMBEDDER", raising=False)
    emb = shared_routing_embedder()
    assert isinstance(emb, HashingEmbedder) and emb.model_name == SHARED_ROUTING_MODEL
    assert routing_embedder_name() == "hashing"


def test_env_names_a_semantic_model_and_wraps_it_in_the_cache(monkeypatch):
    class FakeST:
        def __init__(self, name):
            self.model_name = name

        def embed(self, texts):
            import numpy as np
            return np.ones((len(texts), 4))

    monkeypatch.setenv("ROUTING_EMBEDDER", "fake/model")
    monkeypatch.setattr("nodes.embedding.SentenceTransformerEmbedder", FakeST)
    emb = shared_routing_embedder()
    assert emb.model_name == "fake/model"
    assert type(emb).__name__ == "CachedEmbedder"


def test_coordinator_and_node_agree_on_model_name(monkeypatch, tmp_path):
    """Both ends read the same variable; a node whose local_model equals the
    routing model shares the routing embedder instead of a hashing space."""
    monkeypatch.delenv("ROUTING_EMBEDDER", raising=False)
    state = AppState(instrumentation_path=str(tmp_path / "q.jsonl"))
    state.generator = None
    state.register_node(node_id="n0", documents=["a b c"], policy_labels=[], k=1, sigma=0.0,
                        local_model=state.routing_embedder.model_name)
    assert state.nodes["n0"].local_embedder is state.routing_embedder


def test_server_params_forward_the_routing_embedder_choice(monkeypatch, tmp_path):
    from nodes.mcp_client import _server_params

    monkeypatch.setenv("ROUTING_EMBEDDER", "some/model")
    params = _server_params(tmp_path / "n.json")
    assert params.env["ROUTING_EMBEDDER"] == "some/model"
    assert "--data-file" in params.args


def test_registration_refuses_a_node_in_a_different_routing_space(monkeypatch, tmp_path):
    import asyncio
    import numpy as np
    import pytest

    monkeypatch.delenv("ROUTING_EMBEDDER", raising=False)
    state = AppState(instrumentation_path=str(tmp_path / "q.jsonl"))
    state.generator = None

    class Handle:
        async def get_profile_async(self):
            return {"source_id": "alien", "centroids": np.ones((2, 768)).tolist()}

    monkeypatch.setattr("api.state.MCPNodeHandle", lambda **kw: Handle())
    with pytest.raises(ValueError, match="768-d centroids"):
        asyncio.run(state.register_mcp_node_async(tmp_path / "alien.json"))
