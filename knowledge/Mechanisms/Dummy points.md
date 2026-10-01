---
tags: [type/mechanism]
updated: 2026-09-30
---

# Dummy points

Real probes use fresh random blinding of input-derived group points; dummies use fresh random base-point multiples. In the intended valid prime-order setting their distributions match, hiding which points are useful.

This argument concerns encoded point inputs, not every observable event. Credentials, collection count, failures, response behaviour, session times and client compromise still matter.

See [[Formal leakage]], [[Cover traffic]], [[Threat model]].

## Implementation / Experiment Sources

- [backend/privacy/blind_unlock.py](../../backend/privacy/blind_unlock.py)
- [backend/privacy/psi.py](../../backend/privacy/psi.py)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
