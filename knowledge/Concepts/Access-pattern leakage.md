---
tags: [type/concept]
updated: 2026-09-30
---

# Access-pattern leakage

The contacted-source set can reveal a question's topic even if contents are encrypted. Repeated contact sets may amplify the signal.

All-node blind dispatch fixes the set for an enrolled federation. This addresses source-contact leakage, not every memory-access, timing, table-refresh or session channel. Use the measured attacker and its baseline when describing results.

See [[Topic inference attack]], [[Session attack]], [[Cover traffic]].

## Implementation / Experiment Sources

- [backend/client/device.py](../../backend/client/device.py)
- [docs/41-current-system-specification.md](../../docs/41-current-system-specification.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
