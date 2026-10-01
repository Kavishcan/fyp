---
tags: [type/experiment]
updated: 2026-09-30
---

# Hospital splits

Same 5,000 PMC records and eight nodes:
- K-means in the routing embedding: topic-concentrated partition.
- Dirichlet alpha=.5 over topics: uneven non-IID distribution.
- Random: less specialised distribution.

Per-query topic majority floors: .239/.210/.141. Additional splits challenge the possible advantage of partitioning with the same embedding used to route.

These are three deterministic experimental settings, not evidence across many seeds or real institutions.

See [[Robustness results]], [[Dataset strategy]].

## Implementation / Experiment Sources

- [backend/eval/run_hyfedrag_compare.py](../../backend/eval/run_hyfedrag_compare.py)
- [docs/50-robustness-significance-sessions.md](../../docs/50-robustness-significance-sessions.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
