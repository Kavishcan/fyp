---
tags: [type/mechanism]
updated: 2026-09-30
---

# Unbalanced PSI with precomputation

Large server-side sets motivate setup/online separation: prepare the large representation offline and evaluate a small client input online.

This established idea informs cached blind tables. The prototype is not asserted to implement a specific published PSI protocol exactly or inherit its proof. It combines labelled cluster retrieval, multiple owners and padded all-owner evaluation.

See [[Kiss et al 2017]], [[Labeled PSI]], [[Novelty and contribution]].

## Implementation / Experiment Sources

- [backend/privacy/psi.py](../../backend/privacy/psi.py)
- [docs/47-blind-unlock.md](../../docs/47-blind-unlock.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
