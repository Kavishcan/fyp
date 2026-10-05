---
tags: [type/result]
updated: 2026-10-05
---

# Release results

Gap 3 measurement: records whose text and embedding reach the device per question, against the retrieval output (top-10). PMC, 986 queries, hybrid ranking.

| Clusters (docs per cluster / minimum), P | Records unlocked | × top-10 | MRR |
|---|---|---|---|
| Broadcast (hospitals read the question) | 80 | 8× | .543 |
| 10/5 (default), P=8 | 140 | 14× | .500 |
| 10/5, P=16 | 268 | 27× | .525 |
| **5/5, P=16** | **218** | 22× | **.527** (n.s. vs .525, p = .64) |
| 5/5, P=4 | 59 | 6× | .463 |
| 3/2, P=8 | 57 | 6× | .490 |

**Trade-off:** finer clusters publish centroids closer to single patients. Share within cosine .95 of one patient: 3.6% (10/5) → 7.2% (5/5) → 17.2% (5/3) → 49.4% (3/2). None within .99. The cosine-.90 threshold is uninformative for bge (all centroids pass).

**Wording:** release is measured and tunable, not eliminated. Defaults are unchanged.

**Not run:** membership inference, centroid-to-text inversion, two-level unlock.

See [[Evidence release control]], [[Cluster index]], [[Source-content exposure]].

## Implementation / Experiment Sources

- [docs/56-source-content-release.md](../../docs/56-source-content-release.md)
- [backend/eval/run_release.py](../../backend/eval/run_release.py)
- [docs/results/release_20261002-005108.csv](../../docs/results/release_20261002-005108.csv)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
