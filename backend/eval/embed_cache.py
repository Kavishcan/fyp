"""On-disk embedding cache for the larger evaluation runs (docs/33).

The scaling study embeds tens of thousands of BEIR documents per seed with a
real sentence-transformer, and the same documents recur across source-count
tiers and seeds because they are sampled from the same corpora. Caching by
(model name, exact text) avoids re-encoding them; it does not change any
embedding. The cache key includes the model name so switching models can
never return a vector from a different space.

Cache files live under experiments/cache/ (gitignored) and are safe to delete.
"""
from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = REPO_ROOT / "backend" / "experiments" / "cache"


class CachedEmbedder:
    """Wraps any embedder exposing `.embed(list[str]) -> np.ndarray` and
    `.model_name`. Misses are embedded by the wrapped model in one batch and
    written back; hits are returned from SQLite. Output order matches input.
    """

    def __init__(self, inner, cache_dir: Path | None = None) -> None:
        self.inner = inner
        self.model_name = inner.model_name
        cache_dir = Path(cache_dir or CACHE_DIR)
        cache_dir.mkdir(parents=True, exist_ok=True)
        safe = hashlib.sha256(self.model_name.encode("utf-8")).hexdigest()[:16]
        self._conn = sqlite3.connect(cache_dir / f"embeddings_{safe}.sqlite")
        self._conn.execute("CREATE TABLE IF NOT EXISTS vec (key TEXT PRIMARY KEY, dim INTEGER, data BLOB)")
        self._conn.commit()
        self.hits = 0
        self.misses = 0

    def _key(self, text: str) -> str:
        return hashlib.sha256(f"{self.model_name}\x00{text}".encode("utf-8")).hexdigest()

    def embed(self, texts: list[str]) -> np.ndarray:
        texts = list(texts)
        if not texts:
            return np.empty((0, 0))
        keys = [self._key(t) for t in texts]
        found: dict[str, np.ndarray] = {}
        for start in range(0, len(keys), 900):  # SQLite variable limit
            chunk = keys[start:start + 900]
            rows = self._conn.execute(
                f"SELECT key, dim, data FROM vec WHERE key IN ({','.join('?' * len(chunk))})", chunk
            ).fetchall()
            for key, dim, data in rows:
                found[key] = np.frombuffer(data, dtype=np.float32).astype(np.float64)
        missing = [(k, t) for k, t in zip(keys, texts) if k not in found]
        self.hits += len(texts) - len(missing)
        self.misses += len(missing)
        if missing:
            # Embed each distinct text once even if it appears twice in the batch.
            distinct: dict[str, str] = {}
            for k, t in missing:
                distinct.setdefault(k, t)
            vectors = np.asarray(self.inner.embed(list(distinct.values())), dtype=np.float64)
            self._conn.executemany(
                "INSERT OR REPLACE INTO vec (key, dim, data) VALUES (?, ?, ?)",
                [(k, int(v.shape[0]), v.astype(np.float32).tobytes()) for k, v in zip(distinct, vectors)],
            )
            self._conn.commit()
            for k, v in zip(distinct, vectors):
                found[k] = v
        return np.stack([found[k] for k in keys])

    def embed_one(self, text: str) -> np.ndarray:
        return self.embed([text])[0]

    def __call__(self, texts: list[str]) -> np.ndarray:
        return self.embed(texts)
