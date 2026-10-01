---
tags: [type/mechanism]
updated: 2026-09-30
---

# Key epochs and rotation

Each node's epoch identifies its current OPRF keys. A changed epoch triggers replacement of the corresponding cached table.

**Rotation is not retroactive revocation.** A client retaining old OPRF outputs, derived label keys or plaintext can continue using that knowledge and old tables. Deleting server secrets does not erase client-held secrets. Rotation gates future evaluations and new publications.

Operational schedules, deletion, backup policy and stale-cache behaviour still need validation. See [[Enumeration attack]], [[Source reconciliation]].

## Implementation / Experiment Sources

- [backend/privacy/psi.py](../../backend/privacy/psi.py)
- [backend/privacy/blind_unlock.py](../../backend/privacy/blind_unlock.py)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
