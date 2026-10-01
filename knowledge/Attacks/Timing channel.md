---
tags: [type/attack]
updated: 2026-09-30
---

# Timing channel

Two code-level improvements reduce query-dependent timing:
1. Dispatch to all nodes before local table unlocking.
2. Use one monotonic cover schedule and defer local generation until it finishes.

Neither proves all timing private. Node delays, failed rounds, schedule entry/exit, cache refresh and device contention can remain observable. Direct tick calls do not enforce pacing.

See [[Cover traffic]], [[Formal leakage]], [[Next steps]].

## Implementation / Experiment Sources

- [backend/client/cover.py](../../backend/client/cover.py)
- [backend/privacy/blind_unlock.py](../../backend/privacy/blind_unlock.py)
- [docs/52-standalone-client-and-cover-traffic.md](../../docs/52-standalone-client-and-cover-traffic.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
