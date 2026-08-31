"""Re-exports the shared placeholder embedder for API-layer call sites.

Moved to nodes/embedding.py so a standalone MCP node process
(nodes/mcp_server.py) doesn't need to import the coordinator's API layer.
Kept here so existing `from .embedder import ...` imports in this package
don't need to change.
"""
from nodes.embedding import SHARED_ROUTING_MODEL, HashingEmbedder

__all__ = ["HashingEmbedder", "SHARED_ROUTING_MODEL"]
