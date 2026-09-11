"""Labeled PSI dispatch over an OPRF (docs/03 target architecture, docs/36).

The client holds a few cluster ids (docs/35: the nearest `nprobe` of a node's
published centroids); the node holds every cluster id with an encrypted
envelope of that cluster's passages. The client must learn the envelopes for
its ids and nothing else; the node must not learn which ids were asked, or
whether anything matched. This composes standard pieces — it invents no
cryptography:

  OPRF (DH on the ed25519 prime-order group, libsodium via PyNaCl)
    client:  P = H2C(id);  B = r·P                  (blind, r random)
    node:    E = k·B                                (evaluate with node key k)
    client:  F = r⁻¹·E = k·P                         (unblind)
  The node sees only B, which is uniform in the group — nothing about id.

  Labels: envelope key K_id = KDF(k·P_id, node_id). The node can compute it
  for every id it holds (it knows k); the client can compute it only for ids
  it asked about (it needs the OPRF output). Envelopes are XChaCha20-Poly1305
  under K_id. An envelope for an id the client did not query is opaque.

Delivery: the node must not learn which envelopes matched, so it cannot be
asked for "the matching ones". `Node.envelopes_for(fetch_set)` returns the
envelopes for an anonymity set of cluster ids the CLIENT names; with
`fetch_set = all ids` this is plain labeled PSI (communication linear in the
node's table, node learns nothing); a smaller set trades bytes for the node
learning "one of these". The client can decrypt only the matched ones
either way, so node-side passage disclosure is unaffected by the set size.

Authorization is the OPRF evaluation itself: a node that refuses to evaluate
for an unauthorised credential leaks nothing and serves nothing.

Security rests on DDH in the ed25519 group and on the AEAD; there is no
proof here beyond that reduction. Not measured: side channels, timing,
metadata. `python-paillier` is not involved.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field

import nacl.bindings as sodium

SCALAR_BYTES = sodium.crypto_core_ed25519_SCALARBYTES
POINT_BYTES = sodium.crypto_core_ed25519_BYTES
NONCE_BYTES = sodium.crypto_aead_xchacha20poly1305_ietf_NPUBBYTES
KEY_BYTES = sodium.crypto_aead_xchacha20poly1305_ietf_KEYBYTES
_DOMAIN_H2C = b"fedsaferouter/psi/h2c/v1"
_DOMAIN_KEY = b"fedsaferouter/psi/label-key/v1"


# --- group helpers ------------------------------------------------------------


def random_scalar() -> bytes:
    """Uniform scalar mod the group order (reduce 64 random bytes)."""
    return sodium.crypto_core_ed25519_scalar_reduce(os.urandom(64))


def hash_to_point(item: bytes) -> bytes:
    """Deterministic map of an item to a point on the prime-order subgroup.
    libsodium's from_uniform (Elligator 2) clears the cofactor."""
    uniform = hashlib.sha512(_DOMAIN_H2C + item).digest()[:32]
    return sodium.crypto_core_ed25519_from_uniform(uniform)


def scalar_mult(scalar: bytes, point: bytes) -> bytes:
    """Unclamped scalar multiplication — clamping would break r⁻¹·(r·P) = P."""
    return sodium.crypto_scalarmult_ed25519_noclamp(scalar, point)


def scalar_invert(scalar: bytes) -> bytes:
    return sodium.crypto_core_ed25519_scalar_invert(scalar)


def label_key(oprf_output: bytes, node_id: str) -> bytes:
    return hashlib.blake2b(oprf_output, key=_DOMAIN_KEY, salt=node_id.encode("utf-8")[:16].ljust(16, b"\0"),
                           digest_size=KEY_BYTES).digest()


def encode_cluster_id(cluster_id: int) -> bytes:
    return f"cluster:{int(cluster_id)}".encode("utf-8")


# --- AEAD envelopes -----------------------------------------------------------


def seal(key: bytes, plaintext: bytes) -> bytes:
    nonce = os.urandom(NONCE_BYTES)
    return nonce + sodium.crypto_aead_xchacha20poly1305_ietf_encrypt(plaintext, None, nonce, key)


def open_envelope(key: bytes, envelope: bytes) -> bytes:
    """Raises nacl.exceptions.CryptoError for a wrong key or tampered data."""
    nonce, body = envelope[:NONCE_BYTES], envelope[NONCE_BYTES:]
    return sodium.crypto_aead_xchacha20poly1305_ietf_decrypt(body, None, nonce, key)


# --- client -------------------------------------------------------------------


@dataclass
class BlindedQuery:
    """What leaves the device: blinded points only. `secrets` never leave."""
    blinded: list[bytes]
    secrets: list[bytes] = field(repr=False)
    cluster_ids: list[int] = field(repr=False)


class PSIClient:
    """Device side. Holds nothing but per-query blinding secrets."""

    @staticmethod
    def blind(cluster_ids: list[int]) -> BlindedQuery:
        blinded, secrets = [], []
        for cid in cluster_ids:
            r = random_scalar()
            blinded.append(scalar_mult(r, hash_to_point(encode_cluster_id(cid))))
            secrets.append(r)
        return BlindedQuery(blinded=blinded, secrets=secrets, cluster_ids=list(cluster_ids))

    @staticmethod
    def unblind(query: BlindedQuery, evaluated: list[bytes]) -> list[bytes]:
        if len(evaluated) != len(query.secrets):
            raise ValueError("evaluated points do not match the blinded query")
        return [scalar_mult(scalar_invert(r), e) for r, e in zip(query.secrets, evaluated)]

    @staticmethod
    def open_matches(query: BlindedQuery, oprf_outputs: list[bytes], node_id: str,
                     envelopes: dict[str, bytes]) -> dict[int, list[dict]]:
        """Try every delivered envelope against every queried key. Matches
        decrypt; everything else is opaque. Returns cluster id -> passages.
        Envelope keys are opaque tokens (see Node.envelopes_for), so the
        client learns the cluster id of a match only from its own query."""
        keys = {cid: label_key(out, node_id) for cid, out in zip(query.cluster_ids, oprf_outputs)}
        found: dict[int, list[dict]] = {}
        for token, envelope in envelopes.items():
            for cid, key in keys.items():
                if cid in found:
                    continue
                try:
                    found[cid] = json.loads(open_envelope(key, envelope))
                    break
                except Exception:  # nacl CryptoError: not ours
                    continue
        return found


# --- node ---------------------------------------------------------------------


class PSINode:
    """Node side. Holds the OPRF key and the encrypted cluster table."""

    def __init__(self, node_id: str, key: bytes | None = None) -> None:
        self.node_id = node_id
        self.key = key or random_scalar()
        self.table: dict[int, bytes] = {}          # cluster id -> envelope
        self.tokens: dict[int, str] = {}           # cluster id -> opaque token

    def _label_key(self, cluster_id: int) -> bytes:
        return label_key(scalar_mult(self.key, hash_to_point(encode_cluster_id(cluster_id))), self.node_id)

    def build_table(self, clusters: dict[int, list[dict]]) -> None:
        """`clusters`: cluster id -> passages (each a JSON-serialisable dict).
        Tokens are random, so their order/value reveals nothing about ids."""
        self.table, self.tokens = {}, {}
        for cid, passages in clusters.items():
            self.table[cid] = seal(self._label_key(cid), json.dumps(passages).encode("utf-8"))
            self.tokens[cid] = os.urandom(16).hex()

    def evaluate(self, blinded: list[bytes]) -> list[bytes]:
        """The OPRF step. Input points are uniform; this learns nothing.
        Authorization belongs in front of this call."""
        for point in blinded:
            if len(point) != POINT_BYTES or not sodium.crypto_core_ed25519_is_valid_point(point):
                raise ValueError("invalid blinded point")
        return [scalar_mult(self.key, b) for b in blinded]

    def envelopes_for(self, fetch_set: list[int] | None = None) -> dict[str, bytes]:
        """Envelopes for an anonymity set of cluster ids, keyed by opaque
        token. None = every cluster (full labeled PSI). The node learns the
        set, never which member was wanted."""
        ids = list(self.table) if fetch_set is None else [c for c in fetch_set if c in self.table]
        return {self.tokens[c]: self.table[c] for c in ids}

    def table_bytes(self) -> int:
        return sum(len(v) for v in self.table.values())
