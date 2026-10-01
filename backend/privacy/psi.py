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
from nacl.exceptions import CryptoError

SCALAR_BYTES = sodium.crypto_core_ed25519_SCALARBYTES
POINT_BYTES = sodium.crypto_core_ed25519_BYTES
NONCE_BYTES = sodium.crypto_aead_xchacha20poly1305_ietf_NPUBBYTES
KEY_BYTES = sodium.crypto_aead_xchacha20poly1305_ietf_KEYBYTES
_DOMAIN_H2C = b"fedsaferouter/psi/h2c/v1"
_DOMAIN_KEY = b"fedsaferouter/psi/label-key/v1"
_DOMAIN_TAG = b"fedsaferouter/psi/lookup-tag/v1"
_DOMAIN_NONCE = b"fedsaferouter/psi/nonce/v1"
_DOMAIN_EPOCH = b"fedsaferouter/psi/epoch/v1"
TAG_BYTES = 16


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


def _item_suffix(cluster_id: int | None) -> bytes:
    """2HashDH binds the OPRF input into the outer hash: F_k(x) = H2(x, k·H1(x))
    (Jarecki, Kiayias, Krawczyk). Keys and tags include the cluster id so
    the construction is the one the standard security proof covers (docs/51)."""
    return b"" if cluster_id is None else b"\0item:" + encode_cluster_id(cluster_id)


def label_key(oprf_output: bytes, node_id: str, collection: str = "public", cluster_id: int | None = None) -> bytes:
    """Envelope key. Any collection other than "public" is bound into the key
    (docs/45), so an envelope of one collection can never open with
    another's OPRF output; the cluster id is bound in as the 2HashDH outer
    input (docs/51)."""
    material = oprf_output if collection == "public" else oprf_output + b"\0collection:" + collection.encode("utf-8")
    material += _item_suffix(cluster_id)
    return hashlib.blake2b(material, key=_DOMAIN_KEY, salt=node_id.encode("utf-8")[:16].ljust(16, b"\0"),
                           digest_size=KEY_BYTES).digest()


def encode_cluster_id(cluster_id: int) -> bytes:
    return f"cluster:{int(cluster_id)}".encode("utf-8")


def label_tag(oprf_output: bytes, node_id: str, collection: str = "public", cluster_id: int | None = None) -> bytes:
    """Blind unlock (docs/47): the envelope's lookup label, derived from the
    same OPRF output as its key under a separate domain. Only a holder of
    k·H(id) can compute it, so a published table of tags reveals no id; the
    client that has it finds its envelope by lookup instead of trying every
    envelope against every key."""
    material = oprf_output + b"\0collection:" + collection.encode("utf-8") + _item_suffix(cluster_id)
    return hashlib.blake2b(material, key=_DOMAIN_TAG, salt=node_id.encode("utf-8")[:16].ljust(16, b"\0"),
                           digest_size=TAG_BYTES).digest()


def dummy_point() -> bytes:
    """A cover probe. A real blinded point r·H(id) with r uniform mod the
    group order is a uniform element of the prime-order group (H(id) is a
    generator of it); r·G with r uniform is the same distribution, so a node
    cannot tell the two apart. Fixed-base multiplication is ~7x cheaper than
    blinding a hashed point, and the dummy is most of the per-query work."""
    return sodium.crypto_scalarmult_ed25519_base_noclamp(random_scalar())


# --- compact envelope payload (blind unlock tables) ---------------------------
#
# JSON with float64 embedding lists is ~20 bytes per coordinate; the blind
# table stores embeddings as float16 (2 bytes) after a small JSON header, and
# pads every payload of a table to one length so envelope sizes carry no
# cluster size. Format: b"FSR1" | u32 header length | header JSON |
# float16[n, dim] | zero padding.

_COMPACT_MAGIC = b"FSR1"


def encode_passages(passages: list[dict], embedding_dtype: str = "float16") -> bytes:
    """`embedding_dtype`: "float16" (2 bytes per coordinate) or "int8" (1
    byte, symmetric per-vector scale stored in the header)."""
    import numpy as np

    vectors = np.asarray([p["embedding"] for p in passages], dtype=np.float64) if passages else np.empty((0, 0))
    meta = {"documents": [p["document"] for p in passages],
            "collections": [p.get("collection", "public") for p in passages],
            "dim": int(vectors.shape[1]) if passages else 0, "dtype": embedding_dtype}
    if embedding_dtype == "int8":
        scales = np.maximum(np.abs(vectors).max(axis=1), 1e-12) / 127.0 if passages else np.empty(0)
        meta["scales"] = [float(x) for x in scales]
        body = np.rint(vectors / scales[:, None]).astype(np.int8).tobytes() if passages else b""
    elif embedding_dtype == "float16":
        body = vectors.astype(np.float16).tobytes() if passages else b""
    else:
        raise ValueError("embedding_dtype must be float16 or int8")
    header = json.dumps(meta).encode("utf-8")
    return _COMPACT_MAGIC + len(header).to_bytes(4, "big") + header + body


def decode_passages(payload: bytes) -> list[dict]:
    """Inverse of encode_passages (padding ignored); JSON payloads of the
    per-query PSI table are accepted too."""
    import numpy as np

    if not payload.startswith(_COMPACT_MAGIC):
        return json.loads(payload)
    size = int.from_bytes(payload[4:8], "big")
    header = json.loads(payload[8:8 + size])
    n, dim = len(header["documents"]), header["dim"]
    if header.get("dtype") == "int8":
        flat = np.frombuffer(payload[8 + size:8 + size + n * dim], dtype=np.int8).astype(np.float64)
        vectors = flat.reshape(n, dim) * np.asarray(header["scales"])[:, None] if n else np.empty((0, dim))
    else:
        flat = np.frombuffer(payload[8 + size:8 + size + 2 * n * dim], dtype=np.float16).astype(np.float64)
        vectors = flat.reshape(n, dim) if n else np.empty((0, dim))
    return [{"document": d, "collection": c, "embedding": v.tolist()}
            for d, c, v in zip(header["documents"], header["collections"], vectors)]


def seal_deterministic(key: bytes, plaintext: bytes, aad: bytes = b"") -> bytes:
    """AEAD with the nonce derived from (key, aad, plaintext). A blind-table
    key seals one plaintext per (cluster, chunk) per epoch, so there is no
    nonce reuse across different messages, and every process of a node
    rebuilds a byte-identical table — the device's cached copy stays valid
    across node restarts. `aad` binds the chunk index (docs/47)."""
    nonce = hashlib.blake2b(aad + b"\0" + plaintext, key=key, person=_DOMAIN_NONCE[:16], digest_size=NONCE_BYTES).digest()
    return nonce + sodium.crypto_aead_xchacha20poly1305_ietf_encrypt(plaintext, aad or None, nonce, key)


# --- chunked blind tables (docs/47 addendum) -----------------------------------
#
# Padding every envelope to the node's largest cluster made two thirds of the
# download padding. Instead each cluster's compact payload is compressed and
# split into fixed CHUNK_BYTES chunks, each sealed under the cluster's key with
# its index as associated data and listed under its own tag
# H3(out, cluster, chunk). Tags are pseudorandom, so which chunks belong
# together — hence each cluster's size — is hidden without padding more than
# the last chunk. Compression is applied before encryption; no attacker
# controls any plaintext in a node's table, and chunking hides the lengths.

CHUNK_BYTES = 16384


def chunk_suffix(chunk: int) -> bytes:
    return b"\0chunk:" + str(int(chunk)).encode("ascii")


def chunk_tag(oprf_output: bytes, node_id: str, collection: str, cluster_id: int, chunk: int) -> bytes:
    return label_tag(oprf_output + chunk_suffix(chunk), node_id, collection, cluster_id=cluster_id)


def split_payload(payload: bytes, chunk_bytes: int = CHUNK_BYTES) -> list[bytes]:
    """zlib-compress, then cut into fixed-size chunks (the last zero-padded)."""
    import zlib

    data = zlib.compress(payload, 9)
    chunks = [data[i:i + chunk_bytes] for i in range(0, len(data), chunk_bytes)] or [b""]
    chunks[-1] = chunks[-1] + b"\0" * (chunk_bytes - len(chunks[-1]))
    return chunks


def join_payload(chunks: list[bytes]) -> bytes:
    """Inverse of split_payload: trailing zero padding is ignored by zlib."""
    import zlib

    return zlib.decompressobj().decompress(b"".join(chunks))


# --- AEAD envelopes -----------------------------------------------------------


def seal(key: bytes, plaintext: bytes) -> bytes:
    nonce = os.urandom(NONCE_BYTES)
    return nonce + sodium.crypto_aead_xchacha20poly1305_ietf_encrypt(plaintext, None, nonce, key)


def open_envelope(key: bytes, envelope: bytes, aad: bytes = b"") -> bytes:
    """Raises nacl.exceptions.CryptoError for a wrong key or tampered data."""
    nonce, body = envelope[:NONCE_BYTES], envelope[NONCE_BYTES:]
    return sodium.crypto_aead_xchacha20poly1305_ietf_decrypt(body, aad or None, nonce, key)


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
        keys = {cid: label_key(out, node_id, cluster_id=cid) for cid, out in zip(query.cluster_ids, oprf_outputs)}
        found: dict[int, list[dict]] = {}
        for token, envelope in envelopes.items():
            for cid, key in keys.items():
                if cid in found:
                    continue
                try:
                    found[cid] = json.loads(open_envelope(key, envelope))
                    break
                except CryptoError:  # wrong key or tampered: not ours
                    continue
        return found

    @staticmethod
    def open_matches_multi(query: BlindedQuery, evaluated: list[dict[str, bytes]], node_id: str,
                           envelopes: dict[str, bytes]) -> dict[int, list[dict]]:
        """Role-scoped variant (docs/45): the node returns, per blinded point,
        one evaluation per collection the caller's role may read. Unblind
        each, derive one key per (cluster, collection), try the envelopes.
        Envelopes of collections the node did not evaluate stay opaque."""
        if len(evaluated) != len(query.secrets):
            raise ValueError("evaluated points do not match the blinded query")
        keys: list[tuple[int, bytes]] = []
        for cid, r, per_collection in zip(query.cluster_ids, query.secrets, evaluated):
            inverse = scalar_invert(r)
            for collection, point in per_collection.items():
                keys.append((cid, label_key(scalar_mult(inverse, point), node_id, collection, cluster_id=cid)))
        found: dict[int, list[dict]] = {}
        for envelope in envelopes.values():
            for cid, key in keys:
                if cid in found:
                    continue
                try:
                    found[cid] = decode_passages(open_envelope(key, envelope))
                    break
                except CryptoError:
                    continue
        return found


# --- node ---------------------------------------------------------------------


class PSINode:
    """Node side. Holds the OPRF key and the encrypted cluster table."""

    def __init__(self, node_id: str, key: bytes | None = None, keys: dict[str, bytes] | None = None) -> None:
        """`keys`: one OPRF key per document collection (docs/45). A node with
        a single `key` has one collection, "public" — the original behaviour."""
        self.node_id = node_id
        self.keys: dict[str, bytes] = dict(keys) if keys else {"public": key or random_scalar()}
        self.table: dict[int, bytes] = {}          # cluster id -> envelope
        self.tokens: dict[int, str] = {}           # cluster id -> opaque token
        self.collection_of: dict[int, str] = {}    # cluster id -> collection

    @property
    def key(self) -> bytes:
        """The public collection's key (single-collection nodes: the key)."""
        return self.keys.get("public") or next(iter(self.keys.values()))

    @property
    def collections(self) -> list[str]:
        return sorted(self.keys)

    def _label_key(self, cluster_id: int, collection: str = "public") -> bytes:
        k = self.keys[collection]
        return label_key(scalar_mult(k, hash_to_point(encode_cluster_id(cluster_id))), self.node_id, collection,
                         cluster_id=cluster_id)

    def build_table(self, clusters: dict[int, list[dict]], collection_of: dict[int, str] | None = None) -> None:
        """`clusters`: cluster id -> passages (each a JSON-serialisable dict).
        `collection_of`: cluster id -> collection (default all "public").
        Each envelope is sealed under its own collection's key. Tokens are
        random, so their order/value reveals nothing about ids or collections."""
        self.table, self.tokens, self.collection_of = {}, {}, {}
        self._clusters = clusters
        self._blind = None
        for cid, passages in clusters.items():
            collection = (collection_of or {}).get(cid, "public")
            if collection not in self.keys:
                self.keys[collection] = random_scalar()
            self.collection_of[cid] = collection
            self.table[cid] = seal(self._label_key(cid, collection), json.dumps(passages).encode("utf-8"))
            self.tokens[cid] = os.urandom(16).hex()

    def evaluate(self, blinded: list[bytes]) -> list[bytes]:
        """The OPRF step. Input points are uniform; this learns nothing.
        Authorization belongs in front of this call."""
        for point in blinded:
            if len(point) != POINT_BYTES or not sodium.crypto_core_ed25519_is_valid_point(point):
                raise ValueError("invalid blinded point")
        return [scalar_mult(self.key, b) for b in blinded]

    def evaluate_for(self, blinded: list[bytes], collections: list[str]) -> list[dict[str, bytes]]:
        """Role-scoped OPRF (docs/45): evaluate each blinded point under the
        key of every collection in `collections` (the caller's permitted
        set, decided by the authorizer BEFORE this call). The node still
        learns nothing about which cluster, or which collection, matched; a
        collection not in the set is simply never evaluated, so none of its
        envelopes can open."""
        for point in blinded:
            if len(point) != POINT_BYTES or not sodium.crypto_core_ed25519_is_valid_point(point):
                raise ValueError("invalid blinded point")
        allowed = [c for c in collections if c in self.keys]
        return [{c: scalar_mult(self.keys[c], b) for c in allowed} for b in blinded]

    def envelopes_for(self, fetch_set: list[int] | None = None) -> dict[str, bytes]:
        """Envelopes for an anonymity set of cluster ids, keyed by opaque
        token. None = every cluster (full labeled PSI). The node learns the
        set, never which member was wanted."""
        ids = list(self.table) if fetch_set is None else [c for c in fetch_set if c in self.table]
        return {self.tokens[c]: self.table[c] for c in ids}

    def table_bytes(self) -> int:
        return sum(len(v) for v in self.table.values())

    # --- blind unlock (docs/47) -------------------------------------------------

    @property
    def epoch(self) -> str:
        """Public identifier of the current key set: a keyed hash of the
        OPRF keys (reveals nothing about them). Changes exactly when the keys
        rotate, so a device knows its cached table is stale."""
        h = hashlib.blake2b(key=_DOMAIN_EPOCH, digest_size=8)
        for c in sorted(self.keys):
            h.update(c.encode("utf-8") + b"\0" + self.keys[c])
        return h.hexdigest()

    def rotate_keys(self) -> None:
        """New OPRF keys for every collection and a rebuilt table. Every
        cached copy of the old table becomes permanently unopenable: the node
        no longer evaluates under the keys its envelopes were sealed with."""
        self.keys = {c: random_scalar() for c in self.keys}
        self.build_table(self._clusters, self.collection_of)

    # int8 embeddings in blind tables: MRR unchanged on PMC-Patients
    # (0.421 -> 0.423 at P=8), download 20.7 -> 15.0 MB (docs/47 addendum).
    blind_embedding_dtype = "int8"

    def _build_blind(self) -> dict:
        """Chunk tag -> (collection, envelope): every cluster's payload
        compressed and cut into CHUNK_BYTES chunks, every envelope the same
        length. Deterministic in (keys, clusters, dtype)."""
        entries, groups = {}, []
        for cid, passages in self._clusters.items():
            collection = self.collection_of.get(cid, "public")
            out = scalar_mult(self.keys[collection], hash_to_point(encode_cluster_id(cid)))
            key = label_key(out, self.node_id, collection, cluster_id=cid)
            group = []
            for i, chunk in enumerate(split_payload(encode_passages(passages, self.blind_embedding_dtype))):
                tag = chunk_tag(out, self.node_id, collection, cid, i)
                entries[tag] = (collection, seal_deterministic(key, chunk, aad=chunk_suffix(i)))
                group.append(tag)
            groups.append(group)
        return {"epoch": self.epoch, "dtype": self.blind_embedding_dtype, "entries": entries, "groups": groups}

    def pir_database(self, per_column: int = 1, seed: bytes | None = None):
        """Tier 2 (docs/55): the same sealed chunks as `blind_table`, laid out
        for PIR instead of downloaded whole. Returns (PIRServer, PIRLayout);
        the device downloads the server's hint and the layout's tag map once
        per epoch. Public collection only in this prototype (restricted
        collections would each need their own database)."""
        from privacy.pir import PIRServer, pack

        self.blind_table()                                 # builds or refreshes self._blind
        entries = self._blind["entries"]
        groups = [[(t, entries[t][1]) for t in g] for g in self._blind["groups"] if entries[g[0]][0] == "public"]
        D, layout = pack(groups, len(next(iter(entries.values()))[1]), per_column)
        return PIRServer(D, seed=seed or os.urandom(16)), layout

    def blind_table(self, collections: list[str] | None = None) -> dict:
        """The offline download: every envelope of the permitted collections
        (None = public only), keyed by lookup tag. Every client of the same
        role receives the same bytes, so the download says nothing about any
        question. Restricted collections are served only to roles that may
        read them, so an outsider does not learn their size (audit #6)."""
        if (self._blind is None or self._blind["epoch"] != self.epoch
                or self._blind.get("dtype") != self.blind_embedding_dtype):
            self._blind = self._build_blind()
        allowed = set(collections or ["public"])
        entries = {t: env for t, (c, env) in self._blind["entries"].items() if c in allowed}
        digest = hashlib.blake2b(digest_size=16)
        for tag in sorted(entries):
            digest.update(tag + entries[tag])
        return {"node_id": self.node_id, "epoch": self._blind["epoch"], "version": digest.hexdigest(),
                "entries": entries}
