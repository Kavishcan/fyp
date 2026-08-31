"""Per-query instrumentation, logged from day one so nothing needs rerunning
later (docs/03-architecture.md, docs/04-router-design.md, CLAUDE.md).

Logs one JSON line per query: sources contacted, bytes, per-stage latency,
which passages survived into the final answer, and the full routing decision
(coarse candidates, genuine selection, decoys) so coarse recall and final
recall can always be recomputed and compared separately.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class QueryLog:
    query_id: str
    topic_key: str
    coarse_candidate_ids: list = field(default_factory=list)
    genuine_source_ids: list = field(default_factory=list)
    dispatched_source_ids: list = field(default_factory=list)
    surviving_source_ids: list = field(default_factory=list)
    stage_latency_ms: dict = field(default_factory=dict)
    bytes_transferred: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    extra: dict = field(default_factory=dict)

    @property
    def decoy_source_ids(self) -> list:
        genuine = set(self.genuine_source_ids)
        return [s for s in self.dispatched_source_ids if s not in genuine]


class Instrumentation:
    """Appends one JSON line per query to `path`. Never overwrites — repeated
    runs accumulate, matching the "raw routing output before metrics" record
    required by docs/10-baseline-selection.md.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, log: QueryLog) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(log)) + "\n")

    def read_all(self) -> list[dict]:
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
