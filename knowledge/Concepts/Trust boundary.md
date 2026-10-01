---
tags: [type/concept]
updated: 2026-09-30
---

# Trust boundary

The strict deployment boundary contains the user's device, local embedding model, local generator, plaintext cache, credentials and logs. Node/transport parties are outside it.

An institution-hosted service or enclave can be trusted in a different deployment, but then user-only visibility is no longer the same claim. A hosted API or LLM does not become private because dispatch uses blinding.

See [[Threat model]].

## Implementation / Experiment Sources

- [backend/client/device.py](../../backend/client/device.py)
- [docs/41-current-system-specification.md](../../docs/41-current-system-specification.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
