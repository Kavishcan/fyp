---
tags: [type/experiment]
updated: 2026-09-30
---

# Paired bootstrap

Resample shared evaluation queries with replacement and recompute paired differences or baseline ratios. Archived comparisons use 10,000 resamples.

Report the comparison, confidence interval, split and endpoint together. p>.05 does not establish equality. A near-equal-utility claim should use a pre-specified noninferiority margin and appropriate test. Repeated tuning and multiple comparisons also matter.

See [[Robustness results]], [[Answer quality results]], [[Next steps]].

## Implementation / Experiment Sources

- [backend/eval/bootstrap_compare.py](../../backend/eval/bootstrap_compare.py)
- [docs/50-robustness-significance-sessions.md](../../docs/50-robustness-significance-sessions.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
