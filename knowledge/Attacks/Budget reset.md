---
tags: [type/attack, status/fixed]
---

# Budget reset (audit, docs/49)

The [[Credential gate]] budget lived in process memory; spawn-per-call MCP nodes served **6 of a budget of 2**; restarts reset it; the audit log was never written. Fixed with SQLite persistence. docs/43's bound was not true of real MCP nodes before this.
