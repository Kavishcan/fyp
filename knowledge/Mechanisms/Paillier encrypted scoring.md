---
tags: [type/mechanism, status/experimental]
---

# Paillier encrypted scoring (docs/34)

Experimental in-cluster tier: correct but ~18 s keygen per query, ≤128 rows. The node tool was exposed and unauthenticated — [[Scoring tool embedding theft]] stole every embedding in 3 requests; now off by default, never on gated nodes, public rows only.
