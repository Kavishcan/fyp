---
tags: [hub, research-support]
updated: 2026-09-30
---

# Threat Model and Boundaries

| Party | What It Can See | Assumption / Remaining Risk |
|---|---|---|
| Trusted user device | Query, embedding, selected clusters, opened text, answer | Device, local model and local logs are trusted |
| Node | Credential, permitted collections, P blinded points, request times, budget use | Input hiding is argued for valid fresh group blinding; metadata remains |
| Coalition of nodes | Combined node transcripts and shared external information | Query-independent contact set alone does not protect identity or external side information |
| Network observer | Endpoints, timing, sizes, session participation | Fixed node set and comparable requests; real remote transport still needs hardening |
| Authorised malicious client | Public profiles, permitted caches and legitimately unlocked records | Roles and budgets limit future evaluations, not reuse of already obtained keys/plaintext |
| Malicious source | Its own profile and payload, ability to refuse or poison responses | Authentic signature does not make claims truthful; integrity is not solved |
| Studio/API operator | Raw query and retrieved context in API demonstration path | Must be trusted; use standalone deployment for user-only query visibility |

**Conditional protections**
- All-node fixed-P requests remove the query-dependent contacted-source set in this design.
- Blinding hides requested cluster inputs under the implementation's cryptographic assumptions.
- A finite cover schedule makes scheduled rounds similar; participation, deadline misses, failures and timing outside that schedule remain visible.
- Local generation must really be local. A caller-supplied remote generator changes the boundary.

**Not established:** full end-to-end security against arbitrary malicious nodes, differential privacy, anonymity, clinical de-identification, cache revocation, production Internet deployment, or 1,000-node blind operation.

See [[Formal leakage]], [[Security audit results]], [[Role-scoped publication]], [[Key epochs and rotation]].

## Implementation / Experiment Sources

- [backend/client/device.py](../backend/client/device.py)
- [backend/client/transport.py](../backend/client/transport.py)
- [docs/51-formal-leakage.md](../docs/51-formal-leakage.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
