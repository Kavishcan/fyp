import json

import numpy as np
import pytest

from baselines.base import SourceProfile
from nodes.embedding import HashingEmbedder
from nodes.metadata import attach_metadata, describe_documents
from router.smart import SmartConfig, SmartRouter, SourceEvidence
from eval.run_metadata_pilot import fixed_metadata_ranking


def test_metadata_is_document_only_and_order_invariant():
    documents = ["oncology tumour treatment", "oncology tumour evidence", "cardiology heart"]
    metadata = describe_documents(documents)
    assert metadata == describe_documents(list(reversed(documents)))
    assert metadata["topics"][:2] == ["oncology", "tumour"]
    assert len(metadata["topics"]) <= 16
    assert "Collection topics:" in metadata["description"]


def test_word_repetition_does_not_dominate_document_frequency():
    documents = ["oncology " * 100, "cardiology", "cardiology"]
    assert describe_documents(documents)["topics"][0] == "cardiology"


def test_known_pii_patterns_are_redacted_before_extraction():
    metadata = describe_documents(["Contact jane@example.com at 123-45-6789."])
    assert not {"jane", "example", "com", "redacted"} & set(metadata["topics"])
    assert "123" not in metadata["description"]


def test_empty_documents_have_no_description():
    assert describe_documents([])["description"] == ""
    assert describe_documents(["the and or"])["topics"] == []


def test_metadata_attaches_vector_and_can_be_disabled():
    profile = SourceProfile("a", np.array([[1, 0]]))
    embedder = HashingEmbedder(n_features=2)
    attach_metadata(profile, ["oncology tumour"], embedder)
    assert profile.description_embedding.shape == (2,)
    assert profile.metadata_embedding_model == embedder.model_name
    attach_metadata(profile, ["oncology tumour"], embedder, enabled=False)
    assert profile.description == ""
    assert profile.topics == []
    assert profile.description_embedding is None


def test_description_relevance_changes_ranking_without_remote_probe():
    a = SourceProfile("a", np.array([[1, 0]]), description_embedding=np.array([0, 1]), metadata_embedding_model="toy")
    b = SourceProfile("b", np.array([[0, 1]]), description_embedding=np.array([1, 0]), metadata_embedding_model="toy")
    evidence = {p.source_id: SourceEvidence(authorized=True) for p in [a, b]}
    for mode, expected in [("centroid", "a"), ("description", "b"), ("combined", "a")]:
        result = SmartRouter().route(np.array([1, 0]), [a, b], evidence, SmartConfig(
            relevance_mode=mode, query_model="toy", max_sources=1,
        ))
        assert result.selected_source_ids == [expected]
        if mode == "combined":
            assert result.steps[0]["relevance"] == 0.5
        json.dumps(result.to_dict(), allow_nan=False)


@pytest.mark.parametrize("vector,model", [(None, "toy"), ([1, 0, 0], "toy"),
                                           ([np.nan, 0], "toy"), ([1, 0], "wrong")])
def test_missing_invalid_or_mismatched_metadata_fails_closed(vector, model):
    p = SourceProfile("a", np.array([[1, 0]]), description_embedding=vector, metadata_embedding_model=model)
    result = SmartRouter().route(np.array([1, 0]), [p], {"a": SourceEvidence(authorized=True)},
                                 SmartConfig(relevance_mode="combined", query_model="toy"))
    assert result.selected_source_ids == []
    assert "a" in result.excluded


def test_invalid_metadata_config_rejected():
    with pytest.raises(ValueError):
        SmartConfig(relevance_mode="unknown")
    with pytest.raises(ValueError):
        SmartConfig(description_weight=np.nan)


def test_fixed_control_uses_exact_k_even_with_zero_description_scores():
    profiles = [SourceProfile(str(i), np.array([[1, 0]]), description_embedding=np.array([0, 1]))
                for i in range(4)]
    ids, scores = fixed_metadata_ranking(np.array([1, 0]), profiles, SmartConfig(relevance_mode="description"))
    assert ids == ["0", "1", "2"]
    assert set(scores.values()) == {0}


def test_fixed_scores_match_smart_without_stopping_or_overlap():
    profiles = [SourceProfile(str(i), np.array([[1, i + 1]]),
                              description_embedding=np.array([i + 1, 1])) for i in range(4)]
    evidence = {p.source_id: SourceEvidence(authorized=True) for p in profiles}
    for mode in ("centroid", "description", "combined"):
        config = SmartConfig(relevance_mode=mode, minimum_gain=0, redundancy_weight=0,
                             uncertainty_penalty=0, max_sources=3, exposure_budget=3)
        ids, scores = fixed_metadata_ranking(np.array([1, 0]), profiles, config)
        result = SmartRouter().route(np.array([1, 0]), profiles, evidence, config)
        assert ids == result.selected_source_ids
        for step in result.steps:
            assert step["relevance"] == pytest.approx(scores[step["source_id"]])
