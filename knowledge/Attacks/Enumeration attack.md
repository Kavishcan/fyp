---
tags: [type/attack]
updated: 2026-09-30
---

# Enumeration attack

An authorised client can query many cluster identifiers over time. If C clusters and nprobe probes/round are accessible, roughly ceil(C/nprobe) rounds can enumerate labels, subject to budget and collection policy.

Persistent budgets slow, not prevent, disclosure. Colluding credentials accelerate it; one label holds multiple records, and old authorised keys/plaintext remain usable after rotation.

See [[Credential gate]], [[Key epochs and rotation]].

## Implementation / Experiment Sources

- [backend/eval/run_psi_enumeration.py](../../backend/eval/run_psi_enumeration.py)
- [docs/43-credential-gate.md](../../docs/43-credential-gate.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
