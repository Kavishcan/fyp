"""MCP transport for a source node — added after the in-process pipeline is
stable (docs/04-router-design.md build order, step 9). Deliberately last: the
routing and privacy logic must be correct against InProcessNode first, since
MCP only changes transport, not retrieval semantics.

Not wired up yet. Requires the `mcp` package (already in requirements.txt).
Kept as a thin wrapper so the transport layer cannot silently change retrieval
behaviour relative to InProcessNode — both must return the same
RetrievedPassage shape for the same query.
"""
from __future__ import annotations

from nodes.simulator import InProcessNode


def make_retrieve_tool(node: InProcessNode, embedder, top_n_default: int = 5):
    """Returns a plain callable with the shape an MCP `retrieve` tool needs:
    (query: str) -> list[dict]. Wiring this into an actual `mcp` server
    (stdio or SSE transport, tool registration) is the remaining step — do
    this once real multi-source runs are needed, not before, per the build
    order.
    """

    def retrieve(query: str, top_n: int = top_n_default) -> list[dict]:
        query_embedding = embedder([query])[0]
        passages = node.retrieve(query_embedding, top_n=top_n)
        return [{"document": p.document, "score": p.score} for p in passages]

    return retrieve
