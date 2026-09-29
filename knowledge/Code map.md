---
tags: [hub, type/code]
---

# Code map

| Module | Note |
|---|---|
| `backend/privacy/blind_unlock.py` | [[blind_unlock.py]] |
| `backend/privacy/psi.py` | [[psi.py]] |
| `backend/privacy/cluster_index.py` | [[Cluster index]] |
| `backend/privacy/credentials.py` | [[Credential gate]] |
| `backend/privacy/deidentify.py` | [[Node-side de-identification]] |
| `backend/client/` | [[client package]] |
| `backend/router/hybrid_rerank.py` | [[Hybrid rerank]] |
| `backend/router/anonymity.py` | [[Anonymity cells]] |
| `backend/router/v2.py`, `smart.py` | [[v2 vector dispatch]], [[Smart router]] |
| `backend/nodes/mcp_server.py`, `mcp_client.py` | [[MCP node]] |
| `backend/nodes/signing.py` | [[Profile signing]] |
| `backend/api/state.py` | [[api state]] |
| `backend/eval/` | [[eval harnesses]] |
| `frontend/` | [[studio]] |

Tests: `.venv/bin/pytest -q` (500+). Test counts are not privacy results.
