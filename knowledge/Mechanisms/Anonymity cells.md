---
tags: [type/mechanism]
updated: 2026-09-30
---

# Anonymity cells

Cell routing contacts a group rather than exposing a single source. It reduces some source/topic inference but the selected group can still reveal topic.

Earlier cells are vulnerable to registry-churn intersection and untrusted grouping labels. They are not the current all-node blind design. Measured improvements have utility and residual-leakage costs.

See [[Cells and rerank results]], [[Cell churn intersection]].

## Implementation / Experiment Sources

- [backend/router/anonymity.py](../../backend/router/anonymity.py)
- [docs/40-cells-rerank-healthcare.md](../../docs/40-cells-rerank-healthcare.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
