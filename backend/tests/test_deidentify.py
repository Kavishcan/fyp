"""Node-side de-identification (privacy/deidentify.py, docs/44). These check
the redactor and that NO serving path returns raw PII; they are not a
validation of a clinical de-identifier."""
from __future__ import annotations

import asyncio
import json

import numpy as np
import pytest

from api.state import AppState
from nodes.embedding import HashingEmbedder
from nodes.simulator import build_simulated_source
from privacy.deidentify import Deidentifier, strip_placeholders
from privacy.psi import PSIClient

RECORD = "Patient Rahul Menon, MRN 4432189, DOB 12/03/1984, tel +44 7700 900123, email rahul.m@example.invalid. Chest pain."
VALUES = ["Rahul Menon", "4432189", "12/03/1984", "900123", "rahul.m@example.invalid"]


@pytest.mark.parametrize("text,gone", [
    ("my email is a.b@example.invalid", "a.b@example.invalid"),
    ("MRN 4432189 on file", "4432189"),
    ("NHS 943 476 5919", "943 476 5919"),
    ("DOB 12/03/1984", "12/03/1984"),
    ("born 3 March 1984", "3 March 1984"),
    ("call 555-123-4567", "555-123-4567"),
    ("SSN 123-45-6789", "123-45-6789"),
    ("card 4111 1111 1111 1111", "4111 1111 1111 1111"),
    ("Dr. Sarah O'Neil reviewed", "Sarah O'Neil"),
    ("My name is Test User 001, hi", "Test User 001"),
])
def test_each_identifier_type_is_removed(text, gone):
    assert gone not in Deidentifier().redact(text)


@pytest.mark.parametrize("text", [
    "PCB-153 and GS-9620 were tested in MB-231 cells.",
    "Patient Health Questionnaire scores fell; blood pressure 140/90 mmHg; BMI 31.2.",
    "The trial enrolled 1203 participants between 2004 and 2009.",
    "A range of 186 000-1 415 000 cells.",          # fails Luhn: not a card
])
def test_clinical_and_scientific_text_is_left_alone(text):
    assert Deidentifier().redact(text) == text


def test_bare_name_needs_the_registry():
    text = "Rahul Menon was admitted on the ward."
    assert "Rahul Menon" in Deidentifier().redact(text)
    assert "Rahul Menon" not in Deidentifier(known_identifiers=["Rahul Menon"]).redact(text)


def test_institution_id_format_is_configurable():
    assert "TEST-0042" not in Deidentifier(id_patterns=[r"\bTEST-\d{4}\b"]).redact("ref TEST-0042")


def test_placeholders_never_become_topics():
    assert "NAME" not in strip_placeholders("Patient [NAME] had [DATE] visit").upper()


def _served(node, profile) -> str:
    cids = list(range(len(profile.cluster_centroids)))
    q = PSIClient.blind(cids)
    opened = PSIClient.open_matches(q, PSIClient.unblind(q, node.psi.evaluate(q.blinded)), node.source_id,
                                    node.psi.envelopes_for(None))
    return "\n".join([profile.description, " ".join(profile.topics), *node.documents,
                      *[p["document"] for ps in opened.values() for p in ps]])


def test_no_serving_path_returns_raw_pii():
    docs = [RECORD] + [f"cardiology note {i} about arrhythmia" for i in range(20)]
    node, profile = build_simulated_source("h", docs, HashingEmbedder(), k=2, sigma=0.0, rng=np.random.default_rng(0))
    served = _served(node, profile)
    assert not any(v in served for v in VALUES)


def test_opting_out_reproduces_the_old_leak():
    docs = [RECORD] + [f"cardiology note {i}" for i in range(20)]
    node, profile = build_simulated_source("h", docs, HashingEmbedder(), k=2, sigma=0.0,
                                           rng=np.random.default_rng(0), deidentify=False)
    assert "Rahul Menon" in _served(node, profile)


def test_real_mcp_node_serves_only_deidentified_text(tmp_path):
    data = tmp_path / "hosp.json"
    data.write_text(json.dumps({"node_id": "hosp", "local_model": "toy-e5",
                                "documents": [RECORD] + [f"chest pain note {i}" for i in range(20)]}))
    state = AppState(instrumentation_path=str(tmp_path / "q.jsonl"))
    state.generator = None
    profile = asyncio.run(state.register_mcp_node_async(data))
    served = [profile.description, " ".join(profile.topics)]
    for mode in ("legacy", "psi"):
        r = state.run_query("chest pain patient", max_nodes=1, genuine_k=1, sigma=0.0, routing_mode=mode)
        served += [c["document"] for c in r["citations"]]
    text = "\n".join(served)
    assert "chest pain" in text.lower()
    assert not any(v in text for v in VALUES)
