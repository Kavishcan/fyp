---
tags: [type/concept]
---

# Query leakage

A contacted hospital learns the question (or its topic) from what it receives.

| Mode | Hospital receives | Leak |
|---|---|---|
| text ([[Legacy router]], [[Smart router]], [[HyFedRAG]]-style) | the question | full ([[Privacy cases results]]: 3 of 3 sensitive values) |
| [[v2 vector dispatch]] | an embedding | full via [[Embedding inversion]] (1.000) |
| [[Per-query PSI dispatch]] | blinded cluster ids | none |
| [[Blind unlock]] | P uniform points, real or dummy | none — not even whether it was relevant |

Why it matters: patient details in questions; minimum-necessary sharing rules; question logs leak (AOL 2006); sensitive topics. Not a threat when hospitals are trusted (setting A — use text + [[Broadcast]]).
