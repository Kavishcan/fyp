---
tags: [type/attack, status/fixed]
---

# Open retrieve dump (audit, docs/49)

Gated nodes still served unauthenticated text/vector `retrieve` with unbounded `top_n`: `top_n=100000` returned 60/60 public documents. Fixed: gated nodes refuse open retrieval unless `open_retrieval`; `top_n` capped at 20.
