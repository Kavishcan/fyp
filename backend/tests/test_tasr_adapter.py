"""Tests for the real (not reimplemented) TASR adapter.

Skipped automatically if the upstream repository hasn't been cloned into
backend/vendor/routing-hijacking-fedrag, so the rest of the suite stays green
without the vendor checkout present.
"""
from pathlib import Path

import numpy as np
import pytest

from baselines.base import SourceProfile

VENDOR_PATH = Path(__file__).resolve().parent.parent / "vendor" / "routing-hijacking-fedrag"
pytestmark = pytest.mark.skipif(not VENDOR_PATH.exists(), reason="upstream TASR repo not cloned")


def _profiles():
    return [
        SourceProfile(source_id="honest", centroids=np.array([[1.0, 0.0]])),
        SourceProfile(source_id="attacker", centroids=np.array([[0.9, 0.1]])),
    ]


def test_tasr_adapter_loads_real_upstream_class():
    from baselines.tasr_adapter import TASRAdapter

    adapter = TASRAdapter()
    assert adapter._router.__class__.__name__ == "TrustAwareRouter"


def test_tasr_adapter_registers_and_ranks():
    from baselines.tasr_adapter import TASRAdapter

    adapter = TASRAdapter()
    adapter.register_sources(_profiles())
    result = adapter.rank(np.array([1.0, 0.0]), top_k=1)
    assert result.ranked_source_ids[0] in {"honest", "attacker"}


def test_tasr_adapter_update_trust_runs_without_error():
    from baselines.tasr_adapter import TASRAdapter

    adapter = TASRAdapter()
    adapter.register_sources(_profiles())
    result = adapter.rank(np.array([1.0, 0.0]), top_k=2)
    adapter.update_trust(np.array([1.0, 0.0]), result.ranked_source_ids)
    summary = adapter.trust_summary(malicious_source_ids=["attacker"])
    assert isinstance(summary, dict)


def test_tasr_adapter_missing_vendor_path_raises_clear_error():
    from baselines.tasr_adapter import TASRAdapter

    with pytest.raises(FileNotFoundError, match="git clone"):
        TASRAdapter(vendor_path="/nonexistent/path")
