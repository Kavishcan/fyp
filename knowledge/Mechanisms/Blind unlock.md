---
tags: [type/mechanism]
updated: 2026-09-30
---

# Blind unlock

Download permitted encrypted labelled tables once per epoch. Locally choose global top-P clusters; send P shuffled real/dummy points to every node; collect replies before unblinding and opening cached chunks. Rank and generate locally.

This is query-private **cluster selection with all-node contact**, not selective three-source routing. The planner uses cosine similarity, not the older trust term. Roles, budgets and metadata visibility remain important.

Related: [[Architecture]], [[Chunked blind tables]], [[Formal leakage]], [[Standalone client]].

## Implementation / Experiment Sources

- [backend/privacy/blind_unlock.py](../../backend/privacy/blind_unlock.py)
- [docs/47-blind-unlock.md](../../docs/47-blind-unlock.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
