---
tags: [type/mechanism]
updated: 2026-09-30
---

# Per-query PSI dispatch

Earlier PSI mode privately evaluates selected cluster identifiers but fetches encrypted table data per question. Selection still exposes which nodes are contacted unless combined with cells or all-node dispatch.

The PMC comparison reports high transfer cost; cached blind unlock amortises setup instead. Retain this mode as a historical control, not proof that all PSI protects access patterns.

See [[PSI dispatch results]], [[HyFedRAG comparison results]].

## Implementation / Experiment Sources

- [backend/privacy/psi.py](../../backend/privacy/psi.py)
- [docs/36-psi-dispatch-and-feb4rag.md](../../docs/36-psi-dispatch-and-feb4rag.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
