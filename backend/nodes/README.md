# Source nodes

- mcp_server.py: MCP get_profile and retrieve tools.
- mcp_client.py: client/handle; fresh local subprocess per call.
- profile.py: heuristic redaction, embedding helpers, clustering and empirical profile noise.
- embedding.py: hashing demo encoder and optional SentenceTransformerEmbedder.
- simulator.py: in-process document retrieval and profile construction.

Routing queries and profiles must share a compatible embedding space. Local
retrieval may use a separate space and re-embed the raw question at the source.
The live demo still uses hashing; semantic consistency must be implemented
across both API and MCP before reporting semantic-model results.

MCP retrieves real passages into the coordinator; it does not hide raw questions
from contacted nodes. Regex redaction is not validated de-identification, and
profile noise is not a formal DP guarantee. The simulator holds documents inside
the coordinator, unlike separate MCP processes.

See [architecture](../../docs/03-architecture.md).
