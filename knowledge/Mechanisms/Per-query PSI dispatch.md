---
tags: [type/mechanism, status/superseded]
---

# Per-query PSI dispatch (`routing_mode="psi"`, docs/36)

Contacted nodes receive blinded cluster ids (nprobe per node) and ship their **whole** encrypted table every question (~100 MB/question at PMC scale, ~270 ms). Hides content ([[Query leakage]] = 0) but not the pattern unless combined with [[Anonymity cells]] or [[Broadcast]]. Superseded by [[Blind unlock]] (download once). Still useful where a hospital forbids cached copies. Results: [[PSI dispatch results]], [[HyFedRAG comparison results]].
