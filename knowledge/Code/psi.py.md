---
tags: [type/code]
updated: 2026-09-30
---

# psi.py

Implementation: [psi.py](../../backend/privacy/psi.py).

Group operations, OPRF evaluation/unblinding, label/tag derivation, encrypted labelled tables, float16/int8 payloads, compressed padded chunks, per-collection keys and rotation live here.

Input hiding, table confidentiality, authorisation and disclosure bounds are separate claims. Multi-collection output and cached keys matter; no externally reviewed compositional security proof is established.

See [[OPRF]], [[Formal leakage]], [[Key epochs and rotation]].
