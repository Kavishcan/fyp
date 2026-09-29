---
tags: [type/mechanism]
---

# Presidio NER backend

Optional `presidio_backend()` with spaCy en_core_web_sm, PERSON full names only. Bare names leaked 1.000 → 0.126, 7% of clean docs altered. Stock PERSON+LOCATION catches slightly more (0.081) but alters 66% (84% on PMC case reports) — the [[HyFedRAG]] choice. A clinical transformer is the production choice ([[Future work]]).
