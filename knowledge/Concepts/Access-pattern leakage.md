---
tags: [type/concept]
---

# Access-pattern leakage

*Which* sources were contacted reveals the question's topic — even when content is hidden.

Measured by the [[Topic inference attack]]: cosine router 0.496 vs chance 0.077 on [[FeB4RAG]] ([[Pattern leak results]]); 0.318 vs floor 0.239 on [[PMC-Patients]]. Grows over a [[Session attack]] (0.314 → 0.543).

Defences: [[Topic-stable decoys]] fail (they fingerprint the topic); [[Random decoys]] fall to intersection; [[Anonymity cells]] reduce it; [[Broadcast]] and [[Blind unlock]] remove it (constant contact set). Principle: the anonymity set must be the contacted set ([[Anonymity set]]).
