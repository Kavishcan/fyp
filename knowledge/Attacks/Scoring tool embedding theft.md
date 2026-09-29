---
tags: [type/attack, status/fixed]
---

# Scoring tool embedding theft (audit, docs/49)

The [[Paillier encrypted scoring]] node tool accepted chosen plaintexts (x_j = B^j packs coordinates): **3 unauthenticated requests recovered 100% of embeddings, restricted clinical notes included**. Fixed: off by default, never on gated nodes, public rows only. Regression test in `tests/test_audit_fixes.py`.
