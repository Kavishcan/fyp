---
tags: [type/concept]
---

# MCP node

A hospital's service, one process per source (`nodes/mcp_server.py`). At load: [[Node-side de-identification]] → embeddings → signed profile ([[Profile signing]]) → [[Cluster index]] → PSI/blind tables. Tools: `get_profile`, `psi_evaluate` (gated by [[Credential gate]]), `psi_table`, `get_restricted_centroids`, `psi_envelopes`; open text/vector `retrieve` refused on gated nodes ([[Open retrieve dump]]). The only always-on duty in [[Blind unlock]] is stamping points (~1 ms each). Real network transport (HTTP + TLS) is future work.
