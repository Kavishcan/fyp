---
tags: [type/result]
updated: 2026-09-30
---

# Hybrid rerank results

PMC k-means dense -> hybrid MRR:
- Local HyFedRAG-style: .444 -> .543.
- Blind P=8: .421 -> .509.
- Blind P=24: .437 -> .535.
- Centralised: approximately .443 -> .555.

The latest MIRAGE answers go the other way: .613 dense versus .573 hybrid, p=.07. Ranking benefits are task-dependent; do not label hybrid universally best.

See [[Hybrid rerank]], [[Robustness results]], [[Answer quality results]].

## Implementation / Experiment Sources

- [docs/48-hybrid-rerank.md](../../docs/48-hybrid-rerank.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
