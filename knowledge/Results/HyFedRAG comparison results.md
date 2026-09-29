---
tags: [type/result]
---

# HyFedRAG comparison results (docs/46)

Local reimplementation of [[HyFedRAG]]'s privacy-relevant design on [[PMC-Patients]] (not its code; not comparable to its published numbers).

| Config | MRR | Question to hospitals | Topic (floor 0.239) | Received/q |
|---|---|---|---|---|
| HyFedRAG-style | 0.444 | all 8 | 0.239 | 0.24 MB |
| cosine top-4 | 0.444 | 4 | 0.318 | 0.13 MB |
| PSI + cells | 0.350 | 0 | 0.254 | 103 MB |
| PSI to all 8, nprobe 3 | 0.409 | 0 | 0.239 | 198 MB |

The cost that motivated [[Blind unlock]].
