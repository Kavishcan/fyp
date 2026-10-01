---
tags: [type/concept]
updated: 2026-09-30
---

# Hospital-side PII

Source records can contain identifiers and sensitive clinical content; public case reports are not automatically harmless.

Configured filtering reduces direct identifiers before indexing. Roles and budgets constrain access, but authorised passages, quasi-identifiers and source profiles can still reveal sensitive facts. Public/synthetic experiments are not clinical validation.

See [[Node-side de-identification]], [[Dataset register]], [[Role-scoped publication]].

## Implementation / Experiment Sources

- [backend/client/device.py](../../backend/client/device.py)
- [docs/41-current-system-specification.md](../../docs/41-current-system-specification.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
