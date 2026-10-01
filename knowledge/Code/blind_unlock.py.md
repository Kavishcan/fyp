---
tags: [type/code]
updated: 2026-09-30
---

# blind_unlock.py

Implementation: [blind_unlock.py](../../backend/privacy/blind_unlock.py).

plan_probes performs local cosine-based global cluster selection and per-node padding. cover_plan creates dummy rounds. TableCache stores permitted tables; blind_round sends every node request before refreshing/unlocking.

The cache-current check uses epoch; profile/table version lifecycle deserves further validation. Blind planning has no older trust-weight term.

See [[Blind unlock]], [[Code map]].
