---
tags: [type/mechanism]
updated: 2026-09-30
---

# Profile signing

Ed25519 signatures authenticate a profile relative to a provisioned/pinned key and detect modification. Registry defaults accept unsigned profiles; present invalid signatures are rejected. Pinning is not independent identity verification.

A malicious owner can sign a misleading centroid or poisoned payload. Signatures do not prove truthfulness, prevent Sybils, or establish blind-mode hijack resistance.

See [[Forged profile attack]], [[Trust ranking term]].

## Implementation / Experiment Sources

- [backend/nodes/signing.py](../../backend/nodes/signing.py)
- [backend/router/registry.py](../../backend/router/registry.py)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
