"""
THE POLICY MCP SERVER  (the "bolt on a SECOND tool without touching the agent" proof)
=====================================================================================
A separate MCP server, owned as if by a different team, exposing the two POLICY tools:
the structured jurisdiction NUMBERS and the handbook PROSE search.

Its only job in this week's story is to prove the mentor's checklist item:

    "Can they add a second tool without changing the agent's code?"

The agent discovers tools over MCP, so adding this server to the client's server list
(one line in `run_mcp_agent.py`) gives the agent two more tools. `agent_race/agent.py`
is never edited — the new tools arrive through the existing `gemini_tools` / `dispatch`
hooks, now populated by MCP discovery instead of by hand.

Run directly:
    python3.14 mcp_layer/servers/policy_server.py
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import logging                                     # noqa: E402
logging.getLogger("fastmcp").setLevel(logging.WARNING)

from fastmcp import FastMCP                       # noqa: E402
from agent_race import tools                      # noqa: E402

mcp = FastMCP("policy-server")


@mcp.tool(
    name="get_jurisdiction_rules",
    description=(
        "Return the structured NUMERIC leave parameters for ONE jurisdiction: the tenure "
        "bands (or absence bands) with the exact paid-weeks / cap-days / pay figures and the "
        "governing policy_id and section. Use this ONLY to get the numbers to compute an "
        "entitlement. It knows nothing about any individual employee, and returns data, not prose."
    ),
)
def get_jurisdiction_rules(jurisdiction: str) -> dict:
    """jurisdiction: exactly one of APAC, EMEA, NA, LATAM, UK, ANZ."""
    return tools.get_jurisdiction_rules(jurisdiction)


@mcp.tool(
    name="search_handbook",
    description=(
        "Search the free-text policy handbook and return matching PROSE passages (title + "
        "wording + section). Use this ONLY to find or quote the written wording of a rule — "
        "for example to cite the exact section. It does NOT look up employees and does NOT "
        "return the structured numbers table (use get_jurisdiction_rules for figures)."
    ),
)
def search_handbook(query: str, jurisdiction: str | None = None) -> list:
    """query: free-text rule to find. jurisdiction: optional filter (APAC/EMEA/NA/...)."""
    return tools.search_handbook(query, jurisdiction)


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
