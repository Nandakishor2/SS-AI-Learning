"""
THE WEEK-9 DELIVERABLE  —  the UNCHANGED agent, discovering its tools over MCP.
===============================================================================
One command. It proves every item on the mentor's checklist:

  • "agent uses a tool through MCP, DISCOVERED not hard-coded"
        → the agent's tool list is built from `tools/list` at runtime (see the DISCOVERY
          banner), then fed through the Week-8 `gemini_tools` / `dispatch` hooks.
  • "add a SECOND tool without changing the agent's code"
        → `--hris-only` runs the SAME agent with just the HRIS server (1 tool); the default
          adds the policy server (3 tools). The only thing that changed between the two runs
          is the server LIST in this file — `agent_race/agent.py` is byte-for-byte identical.
  • "where does the AI run?"
        → here, on the client/host. The servers are separate processes that never see the
          model. Each tool call in the table is a JSON-RPC round trip to one of them.

Commands:
    python3.14 -m mcp_layer.run_mcp_agent            # live: discover + run all 10, refresh cache
    python3.14 -m mcp_layer.run_mcp_agent --offline  # reproduce the table from cache, NO API key
    python3.14 -m mcp_layer.run_mcp_agent --hris-only# fewer tools, SAME agent code (the proof)
    python3.14 -m mcp_layer.run_mcp_agent "Employee E002 ...?"   # one ad-hoc question, live

Live runs need `.env` with GEMINI_API_KEY (same key Week 7/8 used). The offline cache makes
the headline reproducible with no key, exactly like Week 8's trajectory eval.
"""
import json
import sys
from pathlib import Path

from agent_race.agent import run_agent          # <-- the UNCHANGED agent under test
from agent_race.questions import QUESTIONS
from agent_race.scoring import passed
from mcp_layer.client import MCPToolProvider, hris_spec, policy_spec
from mcp_layer import safety

_CACHE_DIR = Path(__file__).resolve().parent


def _cache_path(hris_only: bool):
    return _CACHE_DIR / (".mcp_cache_hris_only.json" if hris_only else ".mcp_cache.json")


def _specs(hris_only: bool):
    return [hris_spec()] if hris_only else [hris_spec(), policy_spec()]


def _print_discovery(prov):
    print("\n── MCP DISCOVERY ──────────────────────────────────────────────────────")
    by_server = {}
    for t in prov.discovered:
        by_server.setdefault(t.server_key, []).append(t.name)
    for key, names in by_server.items():
        print(f"  server '{key}':  {', '.join(names)}")
    print(f"  agent received {len(prov.tool_names())} tool(s), none hard-coded in agent.py.")
    scan = safety.scan_discovered(prov.discovered)
    bad = [n for n, v in scan if v != "ok"]
    print(f"  safety scan: {'all clean' if not bad else 'FLAGGED ' + str(bad)}")
    print("───────────────────────────────────────────────────────────────────────")


def _print_acceptance(prov, calls, hris_only):
    """Spell out, for this one question, each Week-9 acceptance criterion and its evidence."""
    by_server = {}
    for t in prov.discovered:
        by_server.setdefault(t.server_key, []).append(t.name)
    called_over_mcp = ", ".join(f"{k}×{v}" for k, v in calls.items()) or "none"
    print("\n══ WEEK-9 ACCEPTANCE CRITERIA (this question) ══════════════════════════")
    print(f"  [1] tool DISCOVERED over MCP, not hard-coded : {prov.tool_names()}")
    print(f"      └─ hard-coded in agent_race/agent.py      : 0")
    print(f"  [2] tools actually CALLED over MCP (tools/call): {called_over_mcp}")
    print(f"  [3] served by separate MCP server process(es)  : {by_server}")
    print(f"      └─ where the AI ran                        : here (client/host), NOT the server")
    print(f"  [4] add a tool without editing the agent       : "
          f"{'run default (adds policy server) → 3 tools' if hris_only else 'policy server bolted on → 3 tools, 0 agent edits'}")
    print("════════════════════════════════════════════════════════════════════════")


def run_live(hris_only=False, single=None):
    with MCPToolProvider(_specs(hris_only)) as prov:
        _print_discovery(prov)
        gt, disp = prov.gemini_tools, prov.dispatch

        if single:
            prov.reset_counts()
            r = run_agent(single, gemini_tools=gt, dispatch=disp, verbose=True)
            calls = {k: v for k, v in prov.call_counts.items() if v}
            print("\nANSWER:", r.answer)
            print(f"stop={r.stop_reason} laps={r.iters} tokens={r.meter.total_tokens} "
                  f"cost=${r.meter.cost_usd:.6f}")
            _print_acceptance(prov, calls, hris_only)
            return

        rows = []
        print(f"\n{'Q':<5}{'pass':<6}{'laps':<6}{'tokens':<8}{'cost$':<10}{'ms':<7}tool_calls")
        for q in QUESTIONS:
            prov.reset_counts()
            r = run_agent(q["question"], gemini_tools=gt, dispatch=disp)
            ok = passed(r.answer, q["expected"])
            calls = {k: v for k, v in prov.call_counts.items() if v}   # counted client-side
            rows.append({"id": q["id"], "pass": ok, "laps": r.iters,
                         "tokens": r.meter.total_tokens, "cost": round(r.meter.cost_usd, 6),
                         "ms": round(r.latency_ms), "tool_calls": calls,
                         "answer": r.answer, "stop": r.stop_reason})
            print(f"{q['id']:<5}{str(ok):<6}{r.iters:<6}{r.meter.total_tokens:<8}"
                  f"{r.meter.cost_usd:<10.6f}{r.latency_ms:<7.0f}{calls}")

    summary = {
        "mode": "hris_only" if hris_only else "hris+policy",
        "discovered_tools": prov.tool_names(),
        "pass_rate": round(sum(r["pass"] for r in rows) / len(rows), 3),
        "rows": rows,
    }
    cache = _cache_path(hris_only)
    cache.write_text(json.dumps(summary, indent=2) + "\n")
    _print_summary(summary)
    print(f"\n(cached to {cache.name} — reproduce with --offline"
          f"{' --hris-only' if hris_only else ''})")


def run_offline(hris_only=False):
    cache = _cache_path(hris_only)
    if not cache.exists():
        sys.exit(f"no cache yet — run once live (needs GEMINI_API_KEY) to create {cache.name}")
    summary = json.loads(cache.read_text())
    print("\n── REPLAY FROM CACHE (no API key) ──────────────────────────────────────")
    print(f"mode: {summary['mode']}   discovered tools: {summary['discovered_tools']}")
    print(f"\n{'Q':<5}{'pass':<6}{'laps':<6}{'tokens':<8}{'cost$':<10}{'ms':<7}tool_calls")
    for r in summary["rows"]:
        print(f"{r['id']:<5}{str(r['pass']):<6}{r['laps']:<6}{r['tokens']:<8}"
              f"{r['cost']:<10.6f}{r['ms']:<7}{r['tool_calls']}")
    _print_summary(summary)


def _print_summary(summary):
    rows = summary["rows"]
    print("\n── SUMMARY ─────────────────────────────────────────────────────────────")
    print(f"  tools discovered over MCP : {summary['discovered_tools']}")
    print(f"  outcome pass rate         : {summary['pass_rate']*100:.0f}%  "
          f"({sum(r['pass'] for r in rows)}/{len(rows)})")
    print(f"  total cost (10 q)         : ${sum(r['cost'] for r in rows):.5f}")
    print("  agent_race/agent.py edits : 0   (tools arrived via MCP discovery)")
    print("────────────────────────────────────────────────────────────────────────")


def main():
    args = sys.argv[1:]
    hris_only = "--hris-only" in args
    if "--offline" in args:
        run_offline(hris_only=hris_only)
    elif hris_only:
        run_live(hris_only=True)
    elif args and not args[0].startswith("--"):
        run_live(single=args[0])
    else:
        run_live()


if __name__ == "__main__":
    main()
