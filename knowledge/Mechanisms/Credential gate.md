---
tags: [type/mechanism]
---

# Credential gate (`privacy/credentials.py`, docs/43)

HMAC over (node, UTC day, blinded points); node allow-list with a per-client daily evaluation budget and an audit line per request; refusal before the OPRF key is touched. Since docs/49 the budget and audit persist in SQLite (`<node>.usage.sqlite`) — before, a spawn-per-call node reset it every call ([[Budget reset]]). Dumping a 150–200-cluster node takes 8–10 days of a 20/day budget. Open issues: shared HMAC key across nodes, replay within a day ([[Security audit results]]). Next: [[Anonymous role tokens]].
