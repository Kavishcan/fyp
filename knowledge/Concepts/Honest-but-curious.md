---
tags: [type/concept]
updated: 2026-09-30
---

# Honest-but-curious

An honest-but-curious party follows the protocol but inspects its transcript. Malicious parties can alter profiles/replies, deny service or exploit endpoint behaviour.

Fresh blinding supports a query-input privacy argument, but a general malicious-server application proof is not established. Content integrity and availability need separate treatment.

See [[Formal leakage]], [[Verifiable OPRF]], [[Forged profile attack]].

## Implementation / Experiment Sources

- [backend/client/device.py](../../backend/client/device.py)
- [docs/41-current-system-specification.md](../../docs/41-current-system-specification.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
