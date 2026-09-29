---
tags: [type/concept]
---

# Device

The user's machine — the only place the question exists. Runs planning, unblinding, unlocking, [[Hybrid rerank]] and [[Local LLM generation]]. Implemented as `client.Device` ([[Standalone client]]); in the studio the API coordinator plays this role. Holds the encrypted table cache ([[Chunked blind tables]]).
