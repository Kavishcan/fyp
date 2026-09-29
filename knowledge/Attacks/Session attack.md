---
tags: [type/attack]
---

# Session attack (`eval/run_session_attack.py`, docs/50)

Five follow-up questions about one patient (967 PMC patients, summary split into five chunks). Topic (floor 0.238) and source (chance 0.125), 1 → 5 questions:

| Policy | Topic | Source |
|---|---|---|
| cosine top-4 | 0.314 → 0.543 | 0.228 → 0.477 |
| topic-stable decoys | 0.469 → 0.570 | 0.190 → 0.252 |
| random decoys | 0.258 → 0.504 | 0.189 → 0.492 |
| cells | 0.256 → 0.283 | 0.183 → 0.200 |
| **blind unlock** | **0.238 → 0.238** | **0.125 → 0.125** |

k-means split only. See [[Session linkage]], [[Robustness results]].
