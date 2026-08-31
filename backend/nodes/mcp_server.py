"""A real, standalone MCP node server — one process per source.

Run it directly:
    python -m nodes.mcp_server --data-file data/mcp_nodes/arguana_1.json

`--data-file` points at a JSON file: {"node_id": str, "local_model": str,
"documents": [str, ...]}. Prepared by scripts/prepare_beir_nodes.py from real
BEIR corpora (see docs/06-datasets.md) — this is not toy data.

This process holds the real documents. It exposes exactly two MCP tools:

- `get_profile`: returns this node's published profile — perturbed centroids
  computed with the SHARED routing embedder, never raw documents. Called once
  by the coordinator when the node comes online.
- `retrieve`: given a query string, re-embeds it with this node's OWN local
  embedder (which may differ from every other node's) and returns the top-n
  passages from its local index. This is the only tool that ever sees a query,
  and the only thing that ever leaves this process besides the profile.

Requires Python 3.10+ (the `mcp` package's floor). See README's MCP section
for why this is a separate venv/interpreter from anything on 3.9.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from mcp.server.mcpserver import MCPServer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # allow `import nodes.*` when run as a script

from nodes.embedding import SHARED_ROUTING_MODEL, HashingEmbedder  # noqa: E402
from nodes.profile import build_profile, embed_documents  # noqa: E402
from nodes.simulator import InProcessNode  # noqa: E402


def load_node(data_file: Path) -> tuple[InProcessNode, dict, str]:
    spec = json.loads(data_file.read_text())
    node_id = spec["node_id"]
    local_model = spec.get("local_model") or SHARED_ROUTING_MODEL
    documents = spec["documents"]

    routing_embedder = HashingEmbedder(model_name=SHARED_ROUTING_MODEL, n_features=256)
    local_embedder = (
        routing_embedder if local_model == SHARED_ROUTING_MODEL else HashingEmbedder(model_name=local_model, n_features=256)
    )

    rng = np.random.default_rng(abs(hash(node_id)) % (2**32))
    routing_embeddings = embed_documents(documents, routing_embedder)
    local_embeddings = (
        routing_embeddings if local_embedder is routing_embedder else embed_documents(documents, local_embedder)
    )

    profile = build_profile(
        node_id,
        routing_embeddings,
        k=min(4, len(documents)),
        sigma=0.05,
        rng=rng,
        document_count=len(documents),
    )
    node = InProcessNode(node_id, documents, local_embeddings, local_embedder=local_embedder)
    return node, profile.__dict__, local_model


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-file", required=True, type=Path)
    args = parser.parse_args()

    node, profile_dict, local_model = load_node(args.data_file)
    server = MCPServer(name=f"fedsaferouter-node-{node.source_id}")

    @server.tool()
    def get_profile() -> str:
        """Return this node's published profile (perturbed centroids only)."""
        serialisable = dict(profile_dict)
        serialisable["centroids"] = np.asarray(serialisable["centroids"]).tolist()
        serialisable["profile_signature"] = serialisable["profile_signature"].hex()
        serialisable["local_model"] = local_model
        return json.dumps(serialisable)

    @server.tool()
    def retrieve(query: str, top_n: int = 5) -> str:
        """Retrieve the top-n locally-held passages for `query`."""
        passages = node.retrieve_from_text(query, top_n=top_n)
        return json.dumps([{"document": p.document, "score": p.score} for p in passages])

    server.run(transport="stdio")


if __name__ == "__main__":
    main()
