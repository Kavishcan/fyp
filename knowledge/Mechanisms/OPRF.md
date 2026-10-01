---
tags: [type/mechanism]
updated: 2026-09-30
---

# OPRF

The client blinds an input-derived group point, the node evaluates it with its secret key, and the client unblinds the result. The prototype uses Ed25519 group operations through PyNaCl.

This prevents the node from seeing the cluster input under the protocol assumptions. It does not authenticate the user's identity anonymously, verify honest server evaluation, or prove application-level disclosure limits.

Read [[Verifiable OPRF]], [[2HashDH key binding]], [[Formal leakage]]. This implementation has not inherited a published malicious-security proof.

## Implementation / Experiment Sources

- [backend/privacy/psi.py](../../backend/privacy/psi.py)
- [docs/51-formal-leakage.md](../../docs/51-formal-leakage.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
