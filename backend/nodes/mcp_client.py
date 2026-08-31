"""Coordinator-side MCP client for a node server (nodes/mcp_server.py).

Deliberately spawns a fresh subprocess per call (connect, call the tool,
close) rather than holding a persistent session open. This trades a small
amount of latency (interpreter + import startup per call, sub-second at the
node sizes used here) for avoiding long-lived-async-resource lifecycle
management inside a synchronous FastAPI app — no shared event loop, no
bridging, no risk of a hung connection outliving a request. A
persistent-session version is a reasonable future optimisation, not a
correctness requirement.

Every call here is a genuine MCP protocol round trip over stdio to a real,
separate OS process — this is not a simulation of MCP, it runs the same
`mcp` SDK a real deployment would use.
"""
from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_SERVER_MODULE = "nodes.mcp_server"
_BACKEND_DIR = str(Path(__file__).resolve().parent.parent)


@dataclass
class MCPNodeHandle:
    """Launch parameters for one node's MCP server. Not a live connection —
    `retrieve` and `get_profile` each open, use, and close their own.
    """

    node_id: str
    data_file: Path

    async def _call_tool(self, tool_name: str, arguments: dict) -> str:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", _SERVER_MODULE, "--data-file", str(self.data_file)],
            cwd=_BACKEND_DIR,
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                if result.is_error:
                    raise RuntimeError(f"MCP tool {tool_name!r} on node {self.node_id!r} failed: {result.content}")
                return result.content[0].text

    async def get_profile_async(self) -> dict:
        return json.loads(await self._call_tool("get_profile", {}))

    async def retrieve_async(self, query: str, top_n: int = 5) -> list[dict]:
        return json.loads(await self._call_tool("retrieve", {"query": query, "top_n": top_n}))

    def get_profile(self) -> dict:
        """Sync wrapper — safe to call from a plain `def` FastAPI handler."""
        return asyncio.run(self.get_profile_async())

    def retrieve_from_text(self, query: str, top_n: int = 5) -> list[dict]:
        """Sync wrapper matching the shape AppState expects for citations."""
        return asyncio.run(self.retrieve_async(query, top_n=top_n))
