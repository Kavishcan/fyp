---
tags: [hub, type/mechanism]
---

# Architecture (recommended: `routing_mode="blind"`, `rerank="hybrid"`)

```text
Offline, once per key epoch
  hospital: de-identify → cluster into boxes → lock each box (per-collection OPRF key)
            → publish signed profile + cluster centroids → publish chunked table
  device:   download every table once (same bytes for every client of a role)

Per question (on the device)
  embed → score every hospital's clusters → global top-P
  → EXACTLY P blinded points to EVERY hospital (real r·H(c) or dummy r·G)
  → each hospital stamps (OPRF) every point, charges its budget
  → unblind real replies → tag lookup in cache → open chunks
  → hybrid rank → top-k evidence → local LLM answer
```

Components: [[Node-side de-identification]] → [[Cluster index]] → [[Chunked blind tables]] → [[Blind unlock]] ([[OPRF]], [[Dummy points]], [[Key epochs and rotation]]) → [[Role-based access]] + [[Credential gate]] → [[Hybrid rerank]] → [[Local LLM generation]]. Runs in the [[Standalone client]] with optional [[Cover traffic]].
