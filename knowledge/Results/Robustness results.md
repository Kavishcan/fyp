---
tags: [type/result]
---

# Robustness results (docs/50)

Hybrid MRR as a share of HyFedRAG-style hybrid ([[Paired bootstrap]]):

| | k-means | Dirichlet | Random |
|---|---|---|---|
| blind P = 8 | 93.6% | 85.8% | 80.7% |
| **blind P = 24** | **98.4% (n.s.)** | **97.4%** | **96.9%** |
| blind vs PSI + cells | +0.071 | +0.073 | +0.067 |

Pattern: blind at the floor on all three; cosine router collapses on random (0.444 → 0.334); cells leak on Dirichlet (0.294 vs 0.210). Always quote the split with a ratio. See [[Hospital splits]], [[Session attack]].
