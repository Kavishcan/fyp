import base64

import numpy as np
import pytest

from baselines.base import SourceProfile
from router.lexical_profile import BYTES, VERSION, build_sketch, buckets, decode_sketch, lexical_scores, fuse_scores
from router.evidence_budget import AllocationConfig, Candidate, allocate


def profiles():
    return [SourceProfile(s, np.array([[1., 0.]]), lexical_sketch=build_sketch([text]), lexical_version=VERSION)
            for s, text in (("a", "common BRCA1 mutation"), ("b", "common pension fund"), ("c", "common mortgage rate"))]


def test_sketch_is_fixed_size_deterministic_and_term_order_independent():
    assert build_sketch(["BRCA1 mutation"]) == build_sketch(["mutation brca1 brca1"])
    assert len(base64.b64decode(build_sketch(["anything"]))) == BYTES
    bits = decode_sketch(build_sketch(["BRCA1 mutation"]))
    assert all(bits[i] == 1 for i in buckets("brca1 mutation"))


def test_discriminative_terms_route_without_raw_documents():
    p = profiles()
    scores = lexical_scores("common brca1", p)
    assert scores == {"a": 1., "b": 0., "c": 0.}
    assert lexical_scores("common", p) is None
    assert lexical_scores("zzzzzqxxxxx", p) is None


def test_missing_corrupt_or_wrong_version_metadata_falls_back_for_every_source():
    p = profiles()
    for value in ("", "bad", base64.b64encode(b"too-short").decode()):
        p[0].lexical_sketch = value
        assert lexical_scores("brca1", p) is None
    p = profiles()
    p[0].lexical_version = "wrong"
    assert lexical_scores("brca1", p) is None


@pytest.mark.parametrize("strategy", ["lexical", "hybrid", "rrf"])
def test_rich_fixed_allocation_has_no_extra_contacts(strategy):
    p = profiles()
    calls = []

    def get(sid, offset):
        calls.append((sid, offset))
        return Candidate(sid, f"{sid}-{offset}", "text", np.array([1., 0.]))

    result = allocate(np.array([1., 0.]), p, get,
                      AllocationConfig(1, 3, method="equal", profile_strategy=strategy, lexical_weight=.5),
                      question="brca1")
    assert result.contacted == ["a"]
    assert calls == [("a", 0), ("a", 1), ("a", 2)]


def test_semantic_zero_weight_parity_and_missing_metadata_fallback():
    semantic = {"a": .8, "b": .7, "c": .6}
    lexical = {"a": 0., "b": 1., "c": .5}
    assert fuse_scores(semantic, lexical, "hybrid", 0) == semantic
    assert fuse_scores(semantic, None, "hybrid", .9) == semantic
    assert max(fuse_scores(semantic, lexical, "hybrid", 1), key=fuse_scores(semantic, lexical, "hybrid", 1).get) == "b"


def test_invalid_configuration_rejected():
    with pytest.raises(ValueError):
        AllocationConfig(profile_strategy="hybrid")
    with pytest.raises(ValueError):
        AllocationConfig(method="equal", profile_strategy="unknown")
    with pytest.raises(ValueError):
        allocate(np.ones(2), profiles(), lambda s, n: None, AllocationConfig(method="equal", profile_strategy="hybrid"))


def test_real_mcp_publishes_sketch_and_hybrid_endpoint_uses_it(tmp_path):
    import asyncio
    import json
    from api.evidence import run_evidence_query
    from api.state import AppState
    state = AppState(str(tmp_path / "queries.jsonl"))
    state.generator = None
    for sid, text in (("a", "brca1 mutation treatment"), ("b", "mortgage pension finance")):
        path = tmp_path / f"{sid}.json"
        path.write_text(json.dumps(dict(node_id=sid, documents=[text], k=1)))
        p = asyncio.run(state.register_mcp_node_async(path))
        assert p.lexical_version == VERSION
        assert len(base64.b64decode(p.lexical_sketch)) == BYTES
    result = run_evidence_query(state, "brca1 treatment",
                               AllocationConfig(1, 1, method="equal", profile_strategy="hybrid"))
    assert result["nodes_contacted"] == ["a"]
    assert result["routing_details"]["requests"] == 1
    assert result["citations"]
