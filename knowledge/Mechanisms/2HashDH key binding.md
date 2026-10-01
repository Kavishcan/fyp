---
tags: [type/mechanism]
updated: 2026-09-30
---

# 2HashDH key binding

Key/tag derivation binds the cluster identifier to the evaluated OPRF output, reducing simple reuse across labels. Study the actual derivation in psi.py.

This is a building block, not a complete cryptographic security audit. A saved authorised output can continue opening its old cached label. Collection multiplicity and multi-chunk labels affect what each evaluation reveals.

See [[Key epochs and rotation]], [[Formal leakage]].

## Implementation / Experiment Sources

- [backend/privacy/psi.py](../../backend/privacy/psi.py)
- [docs/51-formal-leakage.md](../../docs/51-formal-leakage.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
