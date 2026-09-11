"""Experimental Paillier scoring, NOT access-pattern-private RAG.

Trusted coordinator decrypts; honest-but-curious sources score all local rows.
Fixed integer encoding avoids exposing floating-point precision or sparse query
coordinates. No custom cryptographic primitive; python-paillier owns encryption.
"""
from math import gcd
import re

import numpy as np
from phe import paillier

VERSION = "paillier-fixed-dot-v1"
SCALE = 1_000_000
MAX_DIMENSIONS = 1024
MAX_DOCUMENTS = 128
KEY_BITS = 2048


def quantize(values):
    a = np.asarray(values, dtype=float)
    if a.ndim not in (1, 2) or not np.isfinite(a).all():
        raise ValueError("expected finite vector or matrix")
    if not 1 <= a.shape[-1] <= MAX_DIMENSIONS:
        raise ValueError("unsupported dimension")
    norms = np.linalg.norm(a, axis=-1, keepdims=True)
    if not np.isfinite(norms).all():
        raise ValueError("norm overflow")
    return np.rint(a / np.where(norms == 0, 1, norms) * SCALE).astype(np.int64)


def _hex(value, max_length):
    if not isinstance(value, str) or not 1 <= len(value) <= max_length or not re.fullmatch("[0-9a-f]+", value):
        raise ValueError("invalid hexadecimal integer")
    return int(value, 16)


def _ciphertext(public, value):
    width = (public.nsquare.bit_length() + 3)//4
    if not isinstance(value, str) or len(value) != width:
        raise ValueError("invalid ciphertext length")
    c = _hex(value, width)
    if not 0 < c < public.nsquare or gcd(c, public.n) != 1:
        raise ValueError("invalid ciphertext")
    return paillier.EncryptedNumber(public, c, exponent=0)


def _serialize(encrypted):
    width = (encrypted.public_key.nsquare.bit_length() + 3)//4
    return format(encrypted.ciphertext(be_secure=True), f"0{width}x")


class CoordinatorSession:
    """One ephemeral keypair per query; never serialize the private key."""

    def __init__(self, query, model):
        if not isinstance(model, str) or not model or len(model) > 256:
            raise ValueError("invalid model identifier")
        self.query = quantize(query)
        if self.query.ndim != 1:
            raise ValueError("query must be a vector")
        self.model = model
        self.public, self._private = paillier.generate_paillier_keypair(n_length=KEY_BITS)

    def request(self):
        # Encrypt every coordinate afresh, including zeroes, for every recipient.
        return dict(version=VERSION, model=self.model, modulus=format(self.public.n, "x"),
                    ciphertexts=[_serialize(self.public.encrypt(int(x))) for x in self.query])

    def decode(self, response):
        if not isinstance(response, dict) or set(response) != {"version", "model", "scores"}:
            raise ValueError("invalid score response")
        if response["version"] != VERSION or response["model"] != self.model:
            raise ValueError("score protocol mismatch")
        rows = response["scores"]
        if not isinstance(rows, list) or len(rows) > MAX_DOCUMENTS:
            raise ValueError("too many score rows")
        results = []
        for i, row in enumerate(rows):
            if not isinstance(row, dict) or set(row) != {"index", "ciphertext"} or type(row["index"]) is not int or row["index"] != i:
                raise ValueError("invalid score row")
            score = self._private.decrypt(_ciphertext(self.public, row["ciphertext"])) / SCALE**2
            if not np.isfinite(score) or abs(score) > 1.001:
                raise ValueError("score out of range")
            results.append(dict(index=i, score=float(score)))
        return results


def score_encrypted(request, documents, model):
    """Node-only operation: no raw query, private key, top-k or fetch request."""
    if not isinstance(request, dict) or set(request) != {"version", "model", "modulus", "ciphertexts"}:
        raise ValueError("invalid encrypted request")
    if request["version"] != VERSION or request["model"] != model:
        raise ValueError("incompatible protocol or encoder")
    n = _hex(request["modulus"], 512)
    if n.bit_length() != KEY_BITS or n % 2 == 0:
        raise ValueError("unsupported public key")
    encoded = quantize(documents)
    if encoded.ndim != 2 or len(encoded) > MAX_DOCUMENTS:
        raise ValueError("encrypted scoring limited to 128 local rows; no truncation or fallback")
    payload = request["ciphertexts"]
    if not isinstance(payload, list) or len(payload) != encoded.shape[1]:
        raise ValueError("query/index dimension mismatch")
    public = paillier.PaillierPublicKey(n)
    query = [_ciphertext(public, x) for x in payload]
    rows = []
    for i, doc in enumerate(encoded):
        total = public.encrypt(0)
        for j in np.flatnonzero(doc):
            total += query[j] * int(doc[j])
        rows.append(dict(index=i, ciphertext=_serialize(total)))
    return dict(version=VERSION, model=model, scores=rows)
