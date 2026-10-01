---
tags: [type/result]
updated: 2026-09-30
---

# PSI dispatch results

Earlier PSI dispatch is the first tested path not sending query text or embedding to the node. It still reveals contacted sources unless dispatch covers them all.

Historical thirty-node spawn-per-call measurement: roughly 4.85 seconds/query, with substantial table transfer. FeB4RAG local profile ranking: nDCG@1 .734 and MRR .578. These are source-routing metrics, not PMC patient retrieval scores.

See [[Per-query PSI dispatch]], [[FeB4RAG]], [[Scaling and transport results]].

## Implementation / Experiment Sources

- [docs/36-psi-dispatch-and-feb4rag.md](../../docs/36-psi-dispatch-and-feb4rag.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
