---
tags: [type/mechanism]
---

# Cross-node evidence rerank (`evidence_top_k`)

All returned passages re-scored against the question on the device; top-k kept. Drops the attacker's planted passage from the prompt (cited 1.000 → 0.067 at top-2) while the attacker is still selected — a content filter, not a routing defence ([[Cells and rerank results]]).
