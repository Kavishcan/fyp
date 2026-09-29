"""Paired bootstrap on per-query MRR between configurations (docs/50).

Reads the `.perquery.json` that eval/run_hyfedrag_compare.py writes next to
its CSV. Both configurations were scored on the same queries, so the
comparison is paired: resample queries with replacement, recompute the mean
difference (and the ratio) each time. Reports the observed difference, its
95% percentile interval, a two-sided bootstrap p-value (twice the share of
resamples on the far side of zero, capped at 1) and the ratio's interval.

Run: python -m eval.bootstrap_compare <perquery.json> A:B [A:B ...]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def paired_bootstrap(a: np.ndarray, b: np.ndarray, resamples: int = 10_000, seed: int = 0) -> dict:
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    if a.shape != b.shape:
        raise ValueError("paired comparison needs the same queries")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(a), size=(resamples, len(a)))
    ma, mb = a[idx].mean(1), b[idx].mean(1)
    diff, ratio = ma - mb, ma / np.maximum(mb, 1e-12)
    observed = float(a.mean() - b.mean())
    far = np.mean(diff <= 0) if observed > 0 else np.mean(diff >= 0)
    return {"mean_a": float(a.mean()), "mean_b": float(b.mean()), "difference": observed,
            "diff_ci95": [float(np.percentile(diff, 2.5)), float(np.percentile(diff, 97.5))],
            "ratio": float(a.mean() / max(b.mean(), 1e-12)),
            "ratio_ci95": [float(np.percentile(ratio, 2.5)), float(np.percentile(ratio, 97.5))],
            "p_two_sided": float(min(1.0, 2 * far)), "queries": int(len(a)), "resamples": resamples}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("perquery", type=Path)
    parser.add_argument("pairs", nargs="+", help="A:B — configuration A compared with B")
    parser.add_argument("--resamples", type=int, default=10_000)
    args = parser.parse_args()
    data = json.loads(args.perquery.read_text())
    mrr = data["mrr"]
    print(f"{args.perquery.name} (partition {data.get('partition')}, {len(data['query_ids'])} queries)")
    for pair in args.pairs:
        a, b = pair.split(":")
        r = paired_bootstrap(np.array(mrr[a]), np.array(mrr[b]), args.resamples)
        print(f"  {a} vs {b}: MRR {r['mean_a']:.4f} vs {r['mean_b']:.4f} | diff {r['difference']:+.4f} "
              f"[{r['diff_ci95'][0]:+.4f}, {r['diff_ci95'][1]:+.4f}] p={r['p_two_sided']:.4f} | "
              f"ratio {r['ratio']:.3f} [{r['ratio_ci95'][0]:.3f}, {r['ratio_ci95'][1]:.3f}]")


if __name__ == "__main__":
    main()
