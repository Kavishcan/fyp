---
tags: [type/attack]
updated: 2026-09-30
---

# Open retrieve dump

A formerly gated node still served unauthenticated text/vector retrieval with unbounded top_n. Audit fixtures dumped sixty of sixty public documents.

Gated nodes now refuse open retrieval unless explicitly enabled and cap retrieval size. Open/misconfigured nodes have different exposure; endpoint controls do not replace roles or de-identification.

See [[Security audit results]], [[Role-based access]].

## Implementation / Experiment Sources

- [backend/nodes/mcp_server.py](../../backend/nodes/mcp_server.py)
- [docs/49-security-audit.md](../../docs/49-security-audit.md)

These sources support the scoped note; older source prose may require the corrections in [[Source reconciliation]].
