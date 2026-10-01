---
tags: [type/concept]
updated: 2026-09-30
---

# Session linkage

A credential, device and close timestamps can link multiple queries. Hiding query-dependent contacts prevents the measured contact-set attack from improving, but does not make the user anonymous.

Cover traffic can mask real rounds within a fixed schedule. Session start/stop and failures remain observable; anonymous credentials are future work.

See [[Session attack]], [[Anonymous role tokens]].

## Implementation / Experiment Sources

- [backend/client/device.py](../../backend/client/device.py)
- [docs/41-current-system-specification.md](../../docs/41-current-system-specification.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
