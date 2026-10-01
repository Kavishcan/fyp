---
tags: [type/attack]
updated: 2026-09-30
---

# Budget reset

Earlier process-memory usage reset when MCP processes restarted: a budget of two served six evaluations in the audit case. SQLite persistence now records usage and audit across restarts.

Deployment must protect the database and its lifecycle; deleting/resetting it or minting extra credentials changes enforcement.

See [[Credential gate]], [[Security audit results]].

## Implementation / Experiment Sources

- [backend/privacy/credentials.py](../../backend/privacy/credentials.py)
- [docs/49-security-audit.md](../../docs/49-security-audit.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
