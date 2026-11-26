"""
THE HRIS MCP SERVER  (Track C deliverable: "the HRIS server another agent can bolt on")
=======================================================================================
This is the server *I* build and expose so that ANY other person's agent can call it —
not just my own. It speaks MCP over stdio (JSON-RPC). It exposes exactly ONE real thing
this app can do: look up an employee's HR record (the HRIS "source of truth" lookup).

WHERE THE AI RUNS — the honest framing the task asks for:
    The AI does NOT run here. This process is dumb on purpose: it knows how to answer
    `tools/list` and `tools/call`, and nothing about which model (or whose agent) is on
    the other end of the pipe. The host/client side runs the model and DECIDES to call
    this tool; this server just answers. That separation is the entire point of MCP.

REUSE, NOT REIMPLEMENTATION:
    The tool body calls the SAME `agent_race.tools.get_employee_record` the Week-7/8 app
    used in-process. MCP changes only the *transport* (an agent reaches it over a socket
    instead of a Python import) — it is plumbing, it does not make the answer smarter.

Run it directly to hand its stdio to any MCP client:
    python3.14 mcp_layer/servers/hris_server.py
"""
import sys
from pathlib import Path

# Make the Week-9 project root importable when this file is spawned as a subprocess
# (sys.path[0] is this file's dir, not the project root).
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import logging                                     # noqa: E402
logging.getLogger("fastmcp").setLevel(logging.WARNING)   # keep stdout pure JSON-RPC, stderr quiet

from fastmcp import FastMCP                       # noqa: E402
from agent_race import tools                      # noqa: E402  (the REAL app capability)

mcp = FastMCP("hris-server")


@mcp.tool(
    name="get_employee_record",
    # The description is the graded CONTRACT (one job, and what it is NOT) carried over
    # verbatim from the in-process tool so discovery-over-MCP loses nothing.
    description=(
        "Look up ONE employee's HR record by employee_id. Returns that person's name, "
        "jurisdiction, tier, hire_date and computed tenure_months. Use this ONLY to fetch "
        "facts about a specific person. It does NOT contain any policy rule, number, or "
        "handbook text — for those use get_jurisdiction_rules or search_handbook."
    ),
)
def get_employee_record(employee_id: str) -> dict:
    """employee_id: the employee id, e.g. "E002"."""
    return tools.get_employee_record(employee_id)


if __name__ == "__main__":
    # stdio transport: the client spawns this process and talks JSON-RPC over stdin/stdout.
    # Nothing but framed JSON may touch stdout, so all human logging goes to stderr.
    mcp.run(transport="stdio", show_banner=False)
