---
tags: [type/mechanism]
updated: 2026-09-30
---

# Credential gate

Gated nodes authenticate daily requests, apply allow-listed collection permissions, charge point evaluations and persist usage/audit data in SQLite. This closes process-restart budget resets.

At twenty evaluations/day, enumerating 150-200 clusters takes roughly eight-ten days per credential under simple assumptions. Multiple allowed collections, colluding credentials, replay and cached authorised outputs complicate the bound.

Budget use is not a proven one-record-per-evaluation guarantee. See [[Enumeration attack]], [[Budget reset]], [[Formal leakage]].

## Implementation / Experiment Sources

- [backend/privacy/credentials.py](../../backend/privacy/credentials.py)
- [docs/43-credential-gate.md](../../docs/43-credential-gate.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
