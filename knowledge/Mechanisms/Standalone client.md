---
tags: [type/mechanism]
updated: 2026-09-30
---

# Standalone client

The client Device performs local planning, blind dispatch, cached unlock, ranking and optional generation. MCPTransport and LocalTransport share the interface; the CLI runs the path without the Studio API handling the question.

**Conditions:** use local models/generation, configured node permissions and suitable identity/signature policy. The registry permits unsigned profiles by default; a supplied generator could be remote. Neither is automatically a privacy-safe deployment.

See [[Device]], [[Trust boundary]], [[client package]].

## Implementation / Experiment Sources

- [backend/client/device.py](../../backend/client/device.py)
- [backend/router/registry.py](../../backend/router/registry.py)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
