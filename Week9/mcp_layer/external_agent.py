"""
"SOMEONE ELSE'S AGENT"  —  a third party calling MY HRIS server.
================================================================
The mentor asks: "Did they build their own server that ANOTHER PERSON'S agent could call?"
This file stands in for that other person. Crucially, it imports NOTHING from this project's
agent (`agent_race`) — it depends only on the MCP SDK and the public fact that an HRIS server
exists at a known command. That is the reuse MCP is for: a tool you built, used by an agent
that knows nothing about your code.

In production the two sides would be separate repos on separate machines and this client
would point at a URL; here it spawns the same server script over stdio. The boundary is the
same either way: this agent sees only `tools/list` + `tools/call`, never a Python import.

    python3.14 -m mcp_layer.external_agent E002
"""
import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# The ONLY thing a third party needs to know: how to reach the server. (A URL, in prod.)
HRIS_SERVER = Path(__file__).resolve().parents[1] / "mcp_layer" / "servers" / "hris_server.py"


async def run(employee_id: str):
    params = StdioServerParameters(command=sys.executable, args=[str(HRIS_SERVER)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print(f"[external agent] connected to a server I did not write.")

            tools = (await session.list_tools()).tools
            print(f"[external agent] discovered: {[t.name for t in tools]}")

            # A trivial 'agent': it has one task (look up a person) and calls the discovered
            # tool. A real LLM agent would do the same call; the server cannot tell them apart.
            result = await session.call_tool("get_employee_record", {"employee_id": employee_id})
            record = result.structured_content
            print(f"[external agent] get_employee_record({employee_id}) ->")
            print(f"    {record}")
            print("[external agent] I used the HRIS capability with zero knowledge of its code.")
            return record


def main():
    emp = sys.argv[1] if len(sys.argv) > 1 else "E002"
    asyncio.run(run(emp))


if __name__ == "__main__":
    main()
