---
tags: [type/mechanism]
updated: 2026-09-30
---

# Hybrid rerank

The local score combines standardised dense cosine with weighted standardised BM25 over opened passages; the measured default weight is .5. No query text needs to leave the device for this ranking.

PMC retrieval improves substantially in the saved comparisons, but MIRAGE answer accuracy drops from .613 dense to .573 hybrid in the latest run. Choose by task and validated configuration, not universal superiority.

See [[Hybrid rerank results]], [[Answer quality results]].

## Implementation / Experiment Sources

- [backend/router/hybrid_rerank.py](../../backend/router/hybrid_rerank.py)
- [docs/48-hybrid-rerank.md](../../docs/48-hybrid-rerank.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
