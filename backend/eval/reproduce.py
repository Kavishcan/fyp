"""Baseline provenance records (docs/10-baseline-selection.md reproduction
checklist). A baseline result is not a direct benchmark unless this record
exists and every field is filled with an actual value, not a placeholder.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class ReproductionRecord:
    baseline_name: str
    upstream_identity: str  # repository/package/API and exact commit or version
    status: str  # "peer-reviewed" or "preprint"
    licence: str
    environment: str  # OS, Python, dependency versions, model versions
    data: str  # dataset version, source construction, split manifest
    parameters: str  # embedding model, top-k, thresholds, seed
    hardware: str
    interface: str  # inputs, ranked outputs, scores, metrics available
    command: str  # exact reproduction command/configuration
    adaptation: str  # every local change required to run the comparison
    result_path: str  # where the raw per-query routing output is stored
    notes: str = ""
    verified: bool = False
    extra: dict = field(default_factory=dict)


class ReproductionLog:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: ReproductionRecord) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record)) + "\n")

    def read_all(self) -> list[dict]:
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
