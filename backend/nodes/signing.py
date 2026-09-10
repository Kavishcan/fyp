"""Ed25519 signing of published source profiles (v2 integrity, docs/30).

What a valid signature establishes, and only this:
- the profile bytes covered by `signing_payload` were not altered after the
  holder of the private key signed them (tamper detection in transit or in the
  registry), and
- successive profile versions from the same key come from the same holder
  (binding across time, so a third party cannot republish over a node).

What it does NOT establish: who that key holder is (there is no PKI or trust
anchor — the public key travels with the profile), nor that the profile is
truthful. A malicious node signs its forged centroids just as validly as an
honest one. Signatures address impersonation and tampering, not the A3
self-misrepresentation attack; plausibility checks and evidence trust are the
(heuristic) tools for that.

Trust fields (`trust_mean`, `trust_observations`) are coordinator-owned state
and are deliberately excluded from the signed payload.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from baselines.base import SourceProfile

_CENTROID_DECIMALS = 8


def generate_private_key() -> ed25519.Ed25519PrivateKey:
    return ed25519.Ed25519PrivateKey.generate()


def private_key_bytes(key: ed25519.Ed25519PrivateKey) -> bytes:
    return key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )


def private_key_from_bytes(raw: bytes) -> ed25519.Ed25519PrivateKey:
    return ed25519.Ed25519PrivateKey.from_private_bytes(raw)


def public_key_bytes(key: ed25519.Ed25519PrivateKey) -> bytes:
    return key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )


def load_or_create_key_file(path: Path) -> ed25519.Ed25519PrivateKey:
    """A node's persistent private key, kept next to its data file so a fresh
    server process (nodes/mcp_client.py spawns one per call) signs with the
    same identity every time. The file is the node's secret; anyone who can
    read it can sign as that node.
    """
    path = Path(path)
    if path.exists():
        return private_key_from_bytes(path.read_bytes())
    key = generate_private_key()
    path.write_bytes(private_key_bytes(key))
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return key


def signing_payload(profile: SourceProfile) -> bytes:
    """Canonical bytes covered by the signature. Centroids are rounded so the
    payload is identical on both sides of a JSON round trip.
    """
    centroids = np.round(np.asarray(profile.centroids, dtype=np.float64), _CENTROID_DECIMALS).tolist()
    description_embedding = (
        None
        if profile.description_embedding is None
        else np.round(np.asarray(profile.description_embedding, dtype=np.float64), _CENTROID_DECIMALS).tolist()
    )
    body = {
        "source_id": profile.source_id,
        "centroids": centroids,
        "profile_version": profile.profile_version,
        "document_count_bucket": profile.document_count_bucket,
        "policy_labels": list(profile.policy_labels),
        "expected_latency_ms": float(profile.expected_latency_ms),
        "description": profile.description,
        "topics": list(profile.topics),
        "description_embedding": description_embedding,
        "metadata_method": profile.metadata_method,
        "metadata_embedding_model": profile.metadata_embedding_model,
    }
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_profile(profile: SourceProfile, key: ed25519.Ed25519PrivateKey) -> SourceProfile:
    """Sets `profile_signature` and `public_key` in place and returns the profile."""
    profile.public_key = public_key_bytes(key)
    profile.profile_signature = key.sign(signing_payload(profile))
    return profile


def verify_profile(profile: SourceProfile) -> bool:
    """True iff the profile carries a public key and a signature that verifies
    over `signing_payload`. Unsigned profiles return False — callers decide
    whether unsigned is acceptable (router/registry.py `require_signatures`).
    """
    if not profile.public_key or not profile.profile_signature:
        return False
    try:
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(bytes(profile.public_key))
        public_key.verify(bytes(profile.profile_signature), signing_payload(profile))
    except (InvalidSignature, ValueError):
        return False
    return True
