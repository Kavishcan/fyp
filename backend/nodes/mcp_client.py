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

    async def retrieve_vector_async(self, vector, top_n: int = 5) -> list[dict]:
        """v2 dispatch: send a shared-routing-space vector, never the query text."""
        payload = {"vector": [float(x) for x in vector], "top_n": top_n}
        return json.loads(await self._call_tool("retrieve_vector", payload))

    async def psi_evaluate_async(self, blinded: list[bytes]) -> list[bytes]:
        """PSI dispatch: blinded group elements out, evaluated elements back.
        Neither the query text nor its vector is ever an argument here."""
        result = json.loads(await self._call_tool("psi_evaluate", {"blinded": [b.hex() for b in blinded]}))
        return [bytes.fromhex(e) for e in result]

    async def psi_envelopes_async(self, fetch_set: list[int] | None = None) -> dict[str, bytes]:
        result = json.loads(await self._call_tool("psi_envelopes", {"fetch_set": fetch_set}))
        return {token: bytes.fromhex(env) for token, env in result.items()}

    def psi_evaluate(self, blinded: list[bytes]) -> list[bytes]:
        return asyncio.run(self.psi_evaluate_async(blinded))

    def psi_envelopes(self, fetch_set: list[int] | None = None) -> dict[str, bytes]:
        return asyncio.run(self.psi_envelopes_async(fetch_set))

    def get_profile(self) -> dict:
        """Sync wrapper — safe to call from a plain `def` FastAPI handler."""
        return asyncio.run(self.get_profile_async())

    def retrieve_from_text(self, query: str, top_n: int = 5) -> list[dict]:
        """Sync wrapper matching the shape AppState expects for citations."""
        return asyncio.run(self.retrieve_async(query, top_n=top_n))

    def retrieve_vector(self, vector, top_n: int = 5) -> list[dict]:
        return asyncio.run(self.retrieve_vector_async(vector, top_n=top_n))

    def score_encrypted_query(self, request: dict) -> dict:
        """Separate protocol: never falls back to plaintext/vector retrieval."""
        return json.loads(asyncio.run(self._call_tool("score_encrypted_query", {"request": request})))


class PersistentMCPNodeHandle(MCPNodeHandle):
    """Same tools, one long-lived server process and MCP session per node.

    docs/33 measured the spawn-per-call design at ~400–800 ms per contact,
    almost all of it interpreter start-up and profile construction. This
    keeps the subprocess and session open on a private event loop in a
    background thread; every call (sync or async, from any loop) is posted
    to that thread. The privacy properties of the protocol are unchanged —
    the node still receives exactly the same tool arguments. What changes is
    that the node process now persists, so a crash or hang in it must be
    handled by `close()`/re-open rather than by the next call's fresh spawn.
    """

    def __init__(self, node_id: str, data_file: Path) -> None:
        import threading

        super().__init__(node_id=node_id, data_file=data_file)
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, name=f"mcp-{self.node_id}", daemon=True)
        self._thread.start()
        self._session = None
        self._stop = None
        self._ready = None
        # anyio cancel scopes must be entered and exited by the SAME task, so
        # one runner task owns the contexts for the handle's whole life.
        self._runner = asyncio.run_coroutine_threadsafe(self._run(), self._loop)
        ready = asyncio.run_coroutine_threadsafe(self._wait_ready(), self._loop)
        ready.result(timeout=60)

    async def _wait_ready(self) -> None:
        while self._ready is None:
            await asyncio.sleep(0.01)
        await self._ready

    async def _run(self) -> None:
        self._ready = asyncio.get_running_loop().create_future()
        self._stop = asyncio.Event()
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", _SERVER_MODULE, "--data-file", str(self.data_file)],
            cwd=_BACKEND_DIR,
        )
        try:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    self._session = session
                    self._ready.set_result(None)
                    await self._stop.wait()
        except BaseException as exc:  # surface start-up failures to the constructor
            if not self._ready.done():
                self._ready.set_exception(exc)
            raise
        finally:
            self._session = None

    async def _session_call(self, tool_name: str, arguments: dict) -> str:
        result = await self._session.call_tool(tool_name, arguments)
        if result.is_error:
            raise RuntimeError(f"MCP tool {tool_name!r} on node {self.node_id!r} failed: {result.content}")
        return result.content[0].text

    async def _call_tool(self, tool_name: str, arguments: dict) -> str:
        if self._session is None:
            raise RuntimeError(f"node {self.node_id!r} session is closed")
        future = asyncio.run_coroutine_threadsafe(self._session_call(tool_name, arguments), self._loop)
        return await asyncio.wrap_future(future)

    def close(self) -> None:
        """Tear down the session and the server process. Idempotent."""
        if self._loop.is_closed():
            return
        try:
            if self._stop is not None:
                self._loop.call_soon_threadsafe(self._stop.set)
            try:
                self._runner.result(timeout=30)
            except Exception:
                pass  # a runner that failed at start-up already surfaced its error
        finally:
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(timeout=5)
            self._loop.close()
