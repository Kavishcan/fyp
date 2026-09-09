"""A real, standalone MCP node server — one process per source.

Run it directly:
    python -m nodes.mcp_server --data-file data/mcp_nodes/arguana_1.json

`--data-file` points at a JSON file: {"node_id": str, "local_model": str,
"documents": [str, ...]}. Prepared by scripts/prepare_beir_nodes.py from real
BEIR corpora (see docs/06-datasets.md) — this is not toy data.

This process holds the real documents. It exposes exactly two MCP tools:

- `get_profile`: returns this node's published profile: perturbed centroids
  and optional document-derived description/topics/embedding, never raw documents. Called once
  by the coordinator when the node comes online.
- `retrieve`: given a query string, re-embeds it with this node's OWN local
  embedder (which may differ from every other node's) and returns the top-n
  passages from its local index. Only retrieve receives user queries.

Requires Python 3.10+ (the `mcp` package's floor). See README's MCP section
for why this is a separate venv/interpreter from anything on 3.9.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from mcp.server.mcpserver import MCPServer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # allow `import nodes.*` when run as a script

from nodes.embedding import SHARED_ROUTING_MODEL, HashingEmbedder  # noqa: E402
from nodes.profile import build_profile, embed_documents  # noqa: E402
from nodes.simulator import InProcessNode  # noqa: E402
from nodes.metadata import attach_metadata  # noqa: E402


def load_node(data_file: Path) -> tuple[InProcessNode, dict, str]:
    spec = json.loads(data_file.read_text())
    node_id = spec["node_id"]
    local_model = spec.get("local_model") or SHARED_ROUTING_MODEL
    documents = spec["documents"]
    profile_k = spec.get("k", 4)
    if type(profile_k) is not int or profile_k < 1:
        raise ValueError("k must be a positive integer")

    routing_embedder = HashingEmbedder(model_name=SHARED_ROUTING_MODEL, n_features=256)
    local_embedder = (
        routing_embedder if local_model == SHARED_ROUTING_MODEL else HashingEmbedder(model_name=local_model, n_features=256)
    )

    # Profiles must stay reproducible across the fresh process used per call.
    seed = int.from_bytes(hashlib.sha256(node_id.encode()).digest()[:4], "big")
    rng = np.random.default_rng(seed)
    routing_embeddings = embed_documents(documents, routing_embedder)
    local_embeddings = (
        routing_embeddings if local_embedder is routing_embedder else embed_documents(documents, local_embedder)
    )

    profile = build_profile(
        node_id,
        routing_embeddings,
        k=min(profile_k, len(documents)),
        sigma=0.05,
        rng=rng,
        document_count=len(documents),
        policy_labels=spec.get("policy_labels", []),
    )
    attach_metadata(profile, documents, routing_embedder, enabled=spec.get("publish_metadata", True))
    if spec.get("publish_metadata", True):
        from router.lexical_profile import build_sketch, VERSION
        profile.lexical_sketch = build_sketch(documents)
        profile.lexical_version = VERSION
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
        """Return centroids and optional document-derived description/topics."""
        serialisable = dict(profile_dict)
        serialisable["centroids"] = np.asarray(serialisable["centroids"]).tolist()
        serialisable["profile_signature"] = serialisable["profile_signature"].hex()
        if serialisable["description_embedding"] is not None:
            serialisable["description_embedding"] = np.asarray(serialisable["description_embedding"]).tolist()
        serialisable["local_model"] = local_model
        return json.dumps(serialisable)

    @server.tool()
    def retrieve(query: str, top_n: int = 5, offset: int = 0) -> str:
        """Retrieve a ranked page; offset skips already requested passages."""
        passages = node.retrieve_from_text(query, top_n=top_n, offset=offset)
        return json.dumps([{"document": p.document, "score": p.score} for p in passages])

    server.run(transport="stdio")


if __name__ == "__main__":
    main()
