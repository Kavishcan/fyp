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
    # v2 integrity (docs/30): this node's persistent Ed25519 key lives next to
    # its data file so every fresh server process signs with the same identity.
    from nodes.signing import load_or_create_key_file, sign_profile  # noqa: E402

    node = InProcessNode(
        node_id, documents, local_embeddings, local_embedder=local_embedder, routing_embeddings=routing_embeddings
    )
    # PSI dispatch (docs/03 target): the OPRF key persists next to the data
    # file so every fresh server process serves the same table; the cluster
    # index is deterministic in `seed`, so centroids and ids match too.
    from nodes.simulator import attach_psi_index  # noqa: E402
    from privacy.psi import random_scalar  # noqa: E402

    attach_psi_index(node, profile, seed=seed, psi_key=_load_or_create_psi_key(data_file.with_suffix(".psi.key"), random_scalar))
    sign_profile(profile, load_or_create_key_file(data_file.with_suffix(".key")))
    return node, profile.__dict__, local_model


def _load_or_create_psi_key(path: Path, generate) -> bytes:
    if path.exists():
        return bytes.fromhex(path.read_text().strip())
    key = generate()
    path.write_text(key.hex())
    return key


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
        serialisable["public_key"] = serialisable["public_key"].hex()
        if serialisable.get("cluster_centroids") is not None:
            serialisable["cluster_centroids"] = np.asarray(serialisable["cluster_centroids"]).tolist()
        if serialisable["description_embedding"] is not None:
            serialisable["description_embedding"] = np.asarray(serialisable["description_embedding"]).tolist()
        serialisable["local_model"] = local_model
        return json.dumps(serialisable)

    @server.tool()
    def retrieve(query: str, top_n: int = 5) -> str:
        """Retrieve the top-n locally-held passages for `query` (raw text; legacy/smart modes)."""
        passages = node.retrieve_from_text(query, top_n=top_n)
        return json.dumps([{"document": p.document, "score": p.score} for p in passages])

    @server.tool()
    def score_encrypted_query(request: dict) -> str:
        """Experimental full-index encrypted scoring; no document fetch."""
        from privacy.encrypted_scoring import score_encrypted

        return json.dumps(score_encrypted(request, node.routing_embeddings, SHARED_ROUTING_MODEL))

    @server.tool()
    def retrieve_vector(vector: list[float], top_n: int = 5) -> str:
        """v2 dispatch: retrieve by a shared-routing-space vector, never raw text.

        This node never sees the query string in this mode. It is hardening,
        not secrecy — the vector can still be inverted toward the query.
        """
        passages = node.retrieve_vector(np.asarray(vector, dtype=np.float64), top_n=top_n)
        return json.dumps([{"document": p.document, "score": p.score} for p in passages])

    @server.tool()
    def psi_evaluate(blinded: list[str]) -> str:
        """PSI dispatch step 1: OPRF-evaluate blinded points (hex). The node
        learns nothing about the query — the points are uniform in the group.
        Authorization belongs in front of this call."""
        evaluated = node.psi.evaluate([bytes.fromhex(b) for b in blinded])
        return json.dumps([e.hex() for e in evaluated])

    @server.tool()
    def psi_envelopes(fetch_set: list[int] | None = None) -> str:
        """PSI dispatch step 2: encrypted envelopes for an anonymity set of
        cluster ids (None = all). The node learns the set, never the match;
        only envelopes the client holds the OPRF output for will open."""
        envelopes = node.psi.envelopes_for(fetch_set)
        return json.dumps({token: env.hex() for token, env in envelopes.items()})

    server.run(transport="stdio")


if __name__ == "__main__":
    main()
