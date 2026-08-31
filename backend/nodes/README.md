# Nodes

- `server.py` — MCP server exposing a single `retrieve` tool
- `profile.py` — PII removal, local embedding, k-means, Gaussian perturbation
- `simulator.py` — in-process nodes for scaling beyond real MCP

PII removal runs before embedding. If it runs after, embeddings encode the PII and
published centroids inherit it.
