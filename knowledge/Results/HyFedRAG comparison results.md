---
tags: [type/result]
updated: 2026-09-30
---

# HyFedRAG comparison results

This is a **local HyFedRAG-style reimplementation**, not the official implementation or a reproduction of published scores.

Historical PMC k-means dense comparison:
| Condition | MRR | Query Text at Nodes | Transfer / Query |
|---|---|---|---|
| HyFedRAG-style broadcast | .444 | All eight nodes | About .24 MB |
| Cosine top-four | .444 | Four nodes | About .13 MB |
| PSI+cells | .350 | None | About 103 MB |
| PSI to all, nprobe=3 | .409 | None | About 198 MB |

These older per-query-table costs motivated cached [[Blind unlock]]. Current matched hybrid comparison is in [[Robustness results]]. Broadcast's constant contact set already hides source selection, so do not say it leaks both channels.

## Implementation / Experiment Sources

- [docs/46-hyfedrag-comparison.md](../../docs/46-hyfedrag-comparison.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
