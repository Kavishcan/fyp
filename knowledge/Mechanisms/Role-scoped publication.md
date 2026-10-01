---
tags: [type/mechanism]
updated: 2026-09-30
---

# Role-scoped publication

Public metadata is intended to use public documents; permitted restricted centroids are fetched with authorisation. Signed restricted responses are checked when the profile supplies a public key.

**Open issue:** public_view falls back to all documents when no public documents exist, exposing restricted-only source structure. Unsigned-profile defaults also weaken universal signing claims. Do not state that every restricted centroid is hidden.

See [[Source reconciliation]], [[Profile signing]], [[Next steps]].

## Implementation / Experiment Sources

- [backend/nodes/simulator.py](../../backend/nodes/simulator.py)
- [backend/client/device.py](../../backend/client/device.py)
- [docs/45-role-based-access.md](../../docs/45-role-based-access.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
