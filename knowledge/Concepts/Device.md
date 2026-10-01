---
tags: [type/concept]
updated: 2026-09-30
---

# Device

The trusted user machine runs local embedding, cluster selection, unlock, ranking and generation in the standalone path. It holds plaintext and caches.

In the Studio path the API coordinator also sees the raw query. User-only query visibility therefore requires standalone deployment with local models and controlled logs, not simply selecting blind dispatch in a hosted UI.

See [[Trust boundary]], [[Standalone client]].

## Implementation / Experiment Sources

- [backend/client/device.py](../../backend/client/device.py)
- [docs/41-current-system-specification.md](../../docs/41-current-system-specification.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
