"""Single-server PIR for the large-hospital tier of blind unlock (docs/55).

Blind unlock (docs/47) downloads every hospital's sealed table once per key
epoch: about 1.1x the hospital's text. At hospital scale (100 GB of text ->
~110 GB of tables) that download is the part that breaks; the per-question
protocol does not grow with the corpus. Tier 2 replaces the full download
with private information retrieval: the device keeps only a public "hint"
(size independent of the number of columns) and a tag map, and fetches the
sealed chunks of its real clusters with PIR queries the hospital cannot
read. The OPRF round is unchanged and still decides what can be OPENED;
PIR only hides which sealed records were FETCHED.

Scheme: SimplePIR (Henzinger, Hong, Corrigan-Gibbs, Meiklejohn, Vaikuntanathan,
USENIX Security 2023), LWE with n = 1024, q = 2^32, Gaussian error sigma =
6.4, plaintext modulus p = 256 (one byte per entry) — the paper's parameters,
not independently re-estimated here.

  database D   rows x cols bytes (each column holds `per_column` records)
  public A     cols x n, expanded from a public seed
  hint H       D.A mod q (rows x n), downloaded once per epoch
  query        A.s + e + Delta.u_col     (Delta = q / p)
  answer       D.query mod q             (the server touches every byte)
  recover      round((answer - H.s) / Delta) = D[:, col]

Prototype in numpy: the public matrix comes from a seeded PCG64 stream and
the client's secret from a CSPRNG-seeded generator; a deployment would use
an AES/SHAKE expansion as the paper does. Timing is a numpy upper bound, not
the paper's optimised C.
"""
from __future__ import annotations

import hashlib
import os
import secrets
from dataclasses import dataclass, field

import numpy as np

LWE_N = 1024
SIGMA = 6.4
PLAIN_MOD = 256
DELTA = (1 << 32) // PLAIN_MOD
# Decryption error is sum_j D[i,j] e_j: std <= sigma * 255 * sqrt(cols). Keep
# it under Delta/2 by more than 10 standard deviations.
MAX_COLS = 1 << 19
_ROW_BLOCK = 512


def public_matrix(seed: bytes, cols: int) -> np.ndarray:
    """A (cols x n, uint32), expanded from the public seed."""
    state = int.from_bytes(hashlib.blake2b(seed, digest_size=16, person=b"fsr-pir-A").digest(), "big")
    gen = np.random.Generator(np.random.PCG64(state))
    return gen.integers(0, 1 << 32, size=(cols, LWE_N), dtype=np.uint64).astype(np.uint32)


def _mul_mod32(X: np.ndarray, Y: np.ndarray) -> np.ndarray:
    """X @ Y mod 2^32 for unsigned integer matrices, computed EXACTLY with
    float64 BLAS: each operand is split into 16-bit halves, so every partial
    product sum stays below 2^53 (X < 2^32 or a byte, Y < 2^32, inner
    dimension <= MAX_COLS). The hi*hi term is a multiple of 2^32 and drops.
    ~100x faster than numpy's integer matmul, which has no BLAS path."""
    y_lo, y_hi = (Y & 0xFFFF).astype(np.float64), (Y >> 16).astype(np.float64)
    if X.dtype == np.uint8:
        Xf = X.astype(np.float64)
        total = (Xf @ y_lo).astype(np.uint64) + ((Xf @ y_hi).astype(np.uint64) << np.uint64(16))
    else:
        x_lo, x_hi = (X & 0xFFFF).astype(np.float64), (X >> 16).astype(np.float64)
        total = (x_lo @ y_lo).astype(np.uint64) + (((x_lo @ y_hi + x_hi @ y_lo) % 65536.0).astype(np.uint64)
                                                    << np.uint64(16))
    return (total & np.uint64(0xFFFFFFFF)).astype(np.uint32)


def _matmul_mod(D: np.ndarray, M: np.ndarray) -> np.ndarray:
    """D (uint8, rows x cols) @ M (uint32, cols x k) mod 2^32, in row blocks
    so the float copy of D never exceeds one block."""
    out = np.empty((D.shape[0], M.shape[1]), dtype=np.uint32)
    for start in range(0, D.shape[0], _ROW_BLOCK):
        out[start:start + _ROW_BLOCK] = _mul_mod32(D[start:start + _ROW_BLOCK], M)
    return out


@dataclass
class PIRLayout:
    """Public description of a node's PIR database: where each sealed record
    sits. Tags are pseudorandom (privacy/psi.chunk_tag), so the map says
    nothing about which cluster or how large; a device can use it only after
    the OPRF round gave it the tags of its own clusters."""
    record_bytes: int
    per_column: int
    cols: int
    position: dict[bytes, tuple[int, int]]       # tag -> (column, slot)
    max_columns_per_group: int = 1

    @property
    def rows(self) -> int:
        return self.record_bytes * self.per_column

    def map_bytes(self) -> int:
        return sum(len(t) + 4 for t in self.position)


def pack(groups: list[list[tuple[bytes, bytes]]], record_bytes: int, per_column: int,
         rng: np.random.Generator | None = None) -> tuple[np.ndarray, PIRLayout]:
    """Lay groups of equal-length records (one group = one cluster's sealed
    chunks) into columns of `per_column` slots, a group kept in as few
    columns as possible, so one column query usually fetches a whole
    cluster. Empty slots get random bytes (indistinguishable from sealed
    records); column order is shuffled."""
    rng = rng or np.random.default_rng(secrets.randbits(64))
    columns: list[list[tuple[bytes, bytes]]] = []
    open_cols: list[int] = []                     # columns with room left (first-fit scans only these)
    max_span = 1
    for group in sorted(groups, key=len, reverse=True):
        if len(group) > per_column:
            span = -(-len(group) // per_column)
            max_span = max(max_span, span)
            for i in range(span):
                columns.append(list(group[i * per_column:(i + 1) * per_column]))
                if len(columns[-1]) < per_column:
                    open_cols.append(len(columns) - 1)
            continue
        for k, j in enumerate(open_cols):
            if per_column - len(columns[j]) >= len(group):
                columns[j].extend(group)
                if len(columns[j]) == per_column:
                    open_cols.pop(k)
                break
        else:
            columns.append(list(group))
            if len(group) < per_column:
                open_cols.append(len(columns) - 1)
    if len(columns) > MAX_COLS:
        raise ValueError(f"{len(columns)} columns exceeds the correctness bound {MAX_COLS}; raise per_column")
    order = rng.permutation(len(columns))
    D = np.empty((record_bytes * per_column, len(columns)), dtype=np.uint8)
    position: dict[bytes, tuple[int, int]] = {}
    for new_col, old_col in enumerate(order):
        records = columns[old_col]
        for slot in range(per_column):
            if slot < len(records):
                tag, record = records[slot]
                if len(record) != record_bytes:
                    raise ValueError("records must all have the same length")
                position[tag] = (new_col, slot)
                data = record
            else:
                data = os.urandom(record_bytes)
            D[slot * record_bytes:(slot + 1) * record_bytes, new_col] = np.frombuffer(data, dtype=np.uint8)
    return D, PIRLayout(record_bytes=record_bytes, per_column=per_column, cols=len(columns),
                        position=dict(sorted(position.items())), max_columns_per_group=max_span)


@dataclass
class PIRServer:
    """Node side: holds D, publishes the hint, answers query matrices."""
    D: np.ndarray
    seed: bytes = field(default_factory=lambda: os.urandom(16))
    _hint: np.ndarray | None = None

    @property
    def rows(self) -> int:
        return self.D.shape[0]

    @property
    def cols(self) -> int:
        return self.D.shape[1]

    def hint(self) -> np.ndarray:
        """D.A mod q — the per-epoch download: rows x n x 4 bytes, whatever
        the number of columns."""
        if self._hint is None:
            self._hint = _matmul_mod(self.D, public_matrix(self.seed, self.cols))
        return self._hint

    def answer(self, queries: np.ndarray) -> np.ndarray:
        """queries: (k, cols) uint32 -> answers (k, rows). Every byte of D
        takes part, so the node learns nothing about which column was asked."""
        queries = np.asarray(queries, dtype=np.uint32)
        if queries.ndim != 2 or queries.shape[1] != self.cols:
            raise ValueError("query length does not match the database")
        return _matmul_mod(self.D, queries.T).T.copy()


class PIRClient:
    """Device side for one node: the public matrix, the hint and the layout."""

    def __init__(self, seed: bytes, hint: np.ndarray, layout: PIRLayout) -> None:
        self.A = public_matrix(seed, layout.cols)
        self.hint = np.asarray(hint, dtype=np.uint32)
        self.layout = layout
        self._rng = np.random.default_rng(secrets.randbits(128))

    def query(self, col: int) -> tuple[np.ndarray, np.ndarray]:
        s = self._rng.integers(0, 1 << 32, size=LWE_N, dtype=np.uint64).astype(np.uint32)
        e = np.rint(self._rng.normal(0.0, SIGMA, size=self.layout.cols)).astype(np.int64).astype(np.uint32)
        q = _mul_mod32(self.A, s[:, None])[:, 0] + e
        q[col:col + 1] += np.uint32(DELTA)              # array add: wraps mod 2^32 silently
        return q, s

    def recover(self, answer: np.ndarray, s: np.ndarray) -> bytes:
        noisy = np.asarray(answer, dtype=np.uint32) - _mul_mod32(self.hint, s[:, None])[:, 0]
        return (((noisy.astype(np.uint64) + DELTA // 2) >> 24) & 0xFF).astype(np.uint8).tobytes()

    def fetch(self, cols: list[int], answer_fn) -> dict[int, bytes]:
        """Query every column in `cols` (the caller pads to a fixed count),
        one batch to the node, return column -> its bytes."""
        built = [self.query(c) for c in cols]
        answers = np.asarray(answer_fn(np.stack([q for q, _ in built])), dtype=np.uint32)
        # recover all at once: one (rows x n) @ (n x k) product instead of k matrix-vector products
        S = np.stack([s for _, s in built], axis=1)
        noisy = answers - _mul_mod32(self.hint, S).T
        plain = (((noisy.astype(np.uint64) + DELTA // 2) >> 24) & 0xFF).astype(np.uint8)
        return {c: plain[i].tobytes() for i, c in enumerate(cols)}

    def record(self, column: bytes, slot: int) -> bytes:
        r = self.layout.record_bytes
        return column[slot * r:(slot + 1) * r]


def recommended_tier(table_bytes: int, n_records: int, record_bytes: int, per_column: int = 1) -> str:
    """Which tier a node should publish (docs/55). Tier 2 pays a fixed hint
    (rows x n x 4 bytes) plus a 20-byte map entry per record instead of the
    table itself, so it only wins once the table is larger than that. The
    choice depends on the node's size, never on a question."""
    hint = per_column * record_bytes * LWE_N * 4
    return "pir" if hint + 20 * n_records < table_bytes else "download"
