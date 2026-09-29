---
tags: [type/result]
---

# Answer quality results (docs/38, docs/50)

| Condition | Accuracy |
|---|---|
| closed-book | 0.547 |
| PSI + cells + rerank | 0.593 (+0.047, p = 0.10) |
| **blind unlock, dense** | **0.613 (+0.067, CI [+0.007, +0.133], p = 0.035)** |
| blind unlock, hybrid | 0.573 |
| broadcast (docs/38) | 0.627; rerun 0.540 not comparable (machine contention) |

First statistically significant answer gain. See [[MIRAGE]].
