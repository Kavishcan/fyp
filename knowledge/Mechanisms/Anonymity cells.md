---
tags: [type/mechanism, status/superseded]
---

# Anonymity cells (`decoy_policy="cells"`, docs/40)

Sources partitioned once into fixed domain-diverse cells; the whole cell of the top source is contacted. Reduces both leaks on [[FeB4RAG]] (topic 0.454 → 0.201, source 0.744 → 0.231) but leaks the cell: 0.254 vs floor 0.239 on PMC k-means, **0.294 vs 0.210 on Dirichlet**; 0.256 → 0.283 over a session. Weaknesses: [[Cell churn intersection]], self-declared labels. Now the fallback for nodes too large to cache; [[Blind unlock]] recommended. Results: [[Cells and rerank results]].
