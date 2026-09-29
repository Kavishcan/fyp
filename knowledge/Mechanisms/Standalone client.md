---
tags: [type/mechanism, status/recommended]
---

# Standalone client (`backend/client/`, docs/52)

`client.Device` runs the whole [[Blind unlock]] path on the user's machine with **no server in the path**: connect (verify signed profile, download table, fetch restricted centroids, fail closed) → plan (no network) → `blind_round` → finish (rank, generate). Transports: `MCPTransport` (real node process), `LocalTransport` (in-process, gated like the server). CLI: `python -m client`. Removes the caveat "the API process sees the question". Results: [[Client and cover results]].
