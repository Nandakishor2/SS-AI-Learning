"""
THE MCP CLIENT  —  turn one or more MCP servers into the agent's (gemini_tools, dispatch).
==========================================================================================
This is the "host side". It does the three things that make tool use STANDARD instead of
hand-wired:

  1. CONNECT   — spawn each server over stdio and run the JSON-RPC `initialize` handshake.
  2. DISCOVER  — call `tools/list` and learn the tools at RUNTIME (no hard-coded schemas).
  3. ADAPT     — convert each discovered tool into a Gemini FunctionDeclaration, and build
                 a `dispatch` whose functions call the tool back over MCP (`tools/call`).

The result plugs straight into the UNCHANGED Week-8 agent:

    with MCPToolProvider([HRIS, POLICY]) as prov:
        run_agent(question, gemini_tools=prov.gemini_tools, dispatch=prov.dispatch)

`agent_race/agent.py` is never edited. That is the whole deliverable: the agent discovers
its tools instead of us wiring them in, and a second server adds tools with no agent change.

WHY THE THREAD:
    The MCP Python SDK is asyncio-native (streams, sessions, `call_tool` are coroutines).
    The agent loop is synchronous and we are not allowed to touch it. So we run ONE asyncio
    event loop in a background thread that owns every server session for the provider's
    lifetime, and the synchronous `dispatch` submits `call_tool` coroutines to it and blocks
    for the result. Connect/discover/call/close all happen on that single loop (anyio task
    groups must be entered and exited on the same task), which keeps the bridge correct.
"""
import asyncio
import json
import sys
import threading
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from google.genai import types

from mcp_layer.schema_convert import tool_to_declaration
from mcp_layer import safety

_ROOT = Path(__file__).resolve().parents[1]
_PY = sys.executable  # spawn servers with the SAME interpreter running the client


@dataclass
class ServerSpec:
    """How to launch one MCP server over stdio."""
    key: str                      # short label, e.g. "hris"
    script: str                   # path to the server script, relative to project root
    allow: list | None = None     # safety: only these tool names may be used (None = all)


def hris_spec() -> ServerSpec:
    return ServerSpec("hris", "mcp_layer/servers/hris_server.py",
                      allow=["get_employee_record"])


def policy_spec() -> ServerSpec:
    return ServerSpec("policy", "mcp_layer/servers/policy_server.py",
                      allow=["get_jurisdiction_rules", "search_handbook"])


@dataclass
class DiscoveredTool:
    name: str
    description: str
    input_schema: dict
    server_key: str


def _parse_result(result):
    """Normalise an MCP CallToolResult back to the native shape the agent's dispatch returns.

    Our tools return dict (record / rules) or list (handbook). fastmcp wraps a non-dict
    return under {"result": ...} as structured content; we unwrap that so the agent sees
    exactly what the in-process tool used to return.
    """
    if getattr(result, "is_error", False):
        text = ""
        for block in (result.content or []):
            text += getattr(block, "text", "") or ""
        return {"error": text or "tool call failed"}

    sc = getattr(result, "structured_content", None)
    if isinstance(sc, dict):
        if set(sc.keys()) == {"result"}:   # fastmcp's wrapper for a list/scalar return
            return sc["result"]
        return sc

    # Fall back to the text content block, JSON-decoding when possible.
    for block in (result.content or []):
        text = getattr(block, "text", None)
        if text is not None:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
    return {}


class MCPToolProvider:
    """Context manager. On enter: connect + discover. Exposes gemini_tools / dispatch."""

    def __init__(self, specs, startup_timeout=30.0, call_timeout=30.0):
        self.specs = list(specs)
        self.startup_timeout = startup_timeout
        self.call_timeout = call_timeout

        self.discovered: list[DiscoveredTool] = []
        self.call_counts: dict[str, int] = {}    # per-tool call tally (server runs the tool,
                                                 # so the client must count here, not in tools.py)
        self._registry: dict[str, object] = {}   # tool name -> ClientSession
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._stop_evt: asyncio.Event | None = None
        self._error: BaseException | None = None

    # ---- lifecycle -----------------------------------------------------------------
    def __enter__(self):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run, name="mcp-loop", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=self.startup_timeout):
            raise TimeoutError("MCP servers did not finish discovery in time")
        if self._error:
            raise self._error
        return self

    def __exit__(self, *exc):
        if self._loop and self._stop_evt:
            self._loop.call_soon_threadsafe(self._stop_evt.set)
        if self._thread:
            self._thread.join(timeout=self.startup_timeout)
        if self._loop:
            self._loop.close()
        return False

    def _run(self):
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._serve())
        except BaseException as e:   # surfaced to __enter__ via self._error
            self._error = e
            self._ready.set()

    async def _serve(self):
        """Own every session for the provider's lifetime, on this one loop/task."""
        self._stop_evt = asyncio.Event()
        async with AsyncExitStack() as stack:
            for spec in self.specs:
                params = StdioServerParameters(
                    command=_PY,
                    args=[str(_ROOT / spec.script)],
                    cwd=str(_ROOT),
                )
                read, write = await stack.enter_async_context(stdio_client(params))
                session = await stack.enter_async_context(ClientSession(read, write))
                await session.initialize()                       # JSON-RPC handshake
                listed = await session.list_tools()              # DISCOVERY
                for tool in listed.tools:
                    # SAFETY: honour this server's allowlist before trusting any tool.
                    if not safety.tool_is_allowed(spec, tool.name):
                        continue
                    safety.check_tool_trust(spec.key, tool)      # may raise on a suspicious tool
                    self._registry[tool.name] = session
                    self.call_counts[tool.name] = 0
                    self.discovered.append(DiscoveredTool(
                        name=tool.name,
                        description=tool.description or "",
                        input_schema=tool.input_schema or {},
                        server_key=spec.key,
                    ))
            self._ready.set()            # discovery done -> __enter__ unblocks
            await self._stop_evt.wait()  # stay open until __exit__

    # ---- what the agent consumes ---------------------------------------------------
    @property
    def gemini_tools(self):
        """The discovered tools as Gemini function declarations (what run_agent wants)."""
        decls = [tool_to_declaration(t.name, t.description, t.input_schema)
                 for t in self.discovered]
        return [types.Tool(function_declarations=decls)]

    @property
    def dispatch(self):
        """name -> (args:dict)->result, each call routed over MCP to its server."""
        return {t.name: self._make_caller(t.name) for t in self.discovered}

    def tool_names(self):
        return [t.name for t in self.discovered]

    def reset_counts(self):
        for k in self.call_counts:
            self.call_counts[k] = 0

    def _make_caller(self, name):
        def _call(args: dict):
            self.call_counts[name] = self.call_counts.get(name, 0) + 1
            session = self._registry[name]
            fut = asyncio.run_coroutine_threadsafe(
                session.call_tool(name, dict(args or {})), self._loop)
            try:
                result = fut.result(timeout=self.call_timeout)
            except Exception as e:
                return {"error": f"MCP call to {name} failed: {e}"}
            return _parse_result(result)
        return _call


def default_provider():
    """The week's standard setup: HRIS server + the bolted-on policy server."""
    return MCPToolProvider([hris_spec(), policy_spec()])
