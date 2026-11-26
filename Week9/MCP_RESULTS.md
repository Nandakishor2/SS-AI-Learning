<!-- Soft Suave · The AI Engineering League -->
# Week 9 — MCP: the standard socket between the agent and its tools

> **Scope:** Week 9 · Module 5 (MCP, Multi-agent & A2A) · **Track C — HR policy**.
> A direct extension of the Week-7/8 HR agent. Week 8 asked *"is the agent reaching the
> right answer down the right path?"* **Week 9 asks *"can the agent reach its tools the
> standard way — discovering them over MCP instead of us wiring them in — and can someone
> else's agent call a tool we built?"***

The headline is **plumbing, not IQ**: the agent's answers do not change, but *where its
tools come from* does. In Week 8 the three tools were hand-written `FunctionDeclaration`s
compiled into the agent. In Week 9 the agent starts knowing **zero** tools and learns them
at runtime from a `tools/list` call to an MCP server. `agent_race/agent.py` is **edited 0
times** — the tools arrive through the two hooks Week 8 already exposed (`gemini_tools`,
`dispatch`), now populated by MCP discovery.

---

## 1. Headline results

One live run against `gemini-2.5-flash`, cached for no-key replay (`--offline`).

| metric (same 10 HR cases) | Week 8 (tools hard-coded) | **Week 9 (tools over MCP)** |
|---|---:|---:|
| tools in agent source code | 3 | **0** |
| tools discovered at runtime | 0 | **3** (across 2 servers) |
| `agent_race/agent.py` edits to add MCP | — | **0** |
| outcome pass rate | 100% | **100%** (10/10) |
| tool path (every question) | record → rules | **record → rules** (now JSON-RPC calls) |
| cost / 10 q | ~$0.015 | **$0.01522** |

**The "add a second tool without touching the agent" proof** — the same agent, run twice,
changing only the *server list* (one line), never the agent code:

| run | servers wired in | tools the agent discovered | pass rate |
|---|---|---|---:|
| `--hris-only` | HRIS only | `get_employee_record` | **0 / 10** |
| default | HRIS **+** policy | `get_employee_record`, `get_jurisdiction_rules`, `search_handbook` | **10 / 10** |

With only the HRIS server the agent can find *who* the employee is but has no tool for the
*rules numbers*, so it cannot compute the figure — 0/10. Bolting the policy server onto the
client's server list (and nothing else) takes it to 10/10. **Capability tracks the
discovered toolset, not the agent's code.** That is the whole point of MCP.

Per-question record for the default run: [`mcp_layer/.mcp_cache.json`](mcp_layer/.mcp_cache.json).

---

## 2. The commands

> Needs `.env` with `GEMINI_API_KEY` for live runs (same key as Weeks 7–8). Use `python3.14`.
> stdio transport — **no Docker, no ports, no Qdrant**: the client spawns each server as a
> child process and talks JSON-RPC over its stdin/stdout.

```bash
# THE DELIVERABLE: the UNCHANGED agent, discovering its tools over MCP, over all 10 Qs
python3.14 -m mcp_layer.run_mcp_agent              # live: discover + run, refresh cache
python3.14 -m mcp_layer.run_mcp_agent --offline    # reproduce the table from cache, NO API key

# ONE QUESTION, and it prints each acceptance criterion with its evidence (live)
python3.14 -m mcp_layer.run_mcp_agent "Employee E003 is taking primary-caregiver leave. How many weeks of fully paid leave are they entitled to?"
#   -> prints a WEEK-9 ACCEPTANCE CRITERIA block: discovered-not-hardcoded, called over MCP,
#      served by a separate process (AI runs client-side), 2nd tool bolted on with 0 agent edits.

# THE PROOF — same agent, fewer discovered tools, zero code change
python3.14 -m mcp_layer.run_mcp_agent --hris-only          # 1 tool  -> 0/10 (live)
python3.14 -m mcp_layer.run_mcp_agent --hris-only --offline

# SEE THE WIRE once, so MCP stops being a mystery (raw JSON-RPC, no SDK hiding it)
python3.14 -m mcp_layer.handshake

# SOMEONE ELSE'S AGENT calling our HRIS server (imports nothing from agent_race)
python3.14 -m mcp_layer.external_agent E002

# Run a server by hand (hand its stdio to any MCP client / Claude Desktop / Inspector)
python3.14 mcp_layer/servers/hris_server.py
```

---

## 3. Where does the AI actually run? (the question the mentor asks in plain words)

**On the client/host side — never on the tool server.**

```
  ┌─────────────────────────── HOST / CLIENT (our process) ───────────────────────────┐
  │  gemini-2.5-flash  ◄──►  run_agent() loop  ◄──►  MCPToolProvider                    │
  │       (the AI)            (decides WHICH          (discovery + JSON-RPC calls)       │
  │                            tool, WHEN)                    │         │                │
  └──────────────────────────────────────────────────────────┼─────────┼───────────────┘
                                                   stdio      │         │   stdio
                                            (JSON-RPC frames)  ▼         ▼  (JSON-RPC)
                                            ┌──────────────────────┐  ┌──────────────────────┐
                                            │  hris-server (proc)  │  │ policy-server (proc) │
                                            │  get_employee_record │  │ get_jurisdiction_... │
                                            │  — no model here —   │  │ search_handbook      │
                                            └──────────────────────┘  └──────────────────────┘
```

The servers are dumb on purpose. `hris_server.py` can answer `tools/list` and `tools/call`
and **knows nothing about which model (or whose agent) is on the other end of the pipe** —
you can see this directly in [`handshake.py`](mcp_layer/handshake.py): the server's
`initialize` response advertises capabilities and a name, and never asks who is calling. The
model, the agent loop, and the decision to call a tool all live on the host. This is why the
honest client framing is *"MCP wins on reuse and swapping, not on answer quality."*

---

## 4. How each Week-9 requirement is met

| # | Requirement | Where |
|---|---|---|
| 1 | Agent discovers a tool over MCP (not hard-coded) | [`mcp_layer/client.py`](mcp_layer/client.py) runs `initialize` → `tools/list`, converts each tool's JSON-Schema to a Gemini decl ([`schema_convert.py`](mcp_layer/schema_convert.py)), and feeds it through the existing `gemini_tools`/`dispatch` hooks |
| 2 | Add a second tool **without changing the agent** | §1 proof table: `--hris-only` (1 tool) vs default (3 tools); the diff is the server list in [`run_mcp_agent.py`](mcp_layer/run_mcp_agent.py), **0 edits** to `agent_race/agent.py` |
| 3 | Build our own server another person's agent can call | [`mcp_layer/servers/hris_server.py`](mcp_layer/servers/hris_server.py) (the HRIS capability) + [`mcp_layer/external_agent.py`](mcp_layer/external_agent.py), a client that imports **nothing** from `agent_race` and calls it |
| 4 | Explain where the AI runs | §3 above; demonstrated by [`handshake.py`](mcp_layer/handshake.py) |
| Safety | Access control + checking a tool before trusting someone else's | [`mcp_layer/safety.py`](mcp_layer/safety.py): per-server **allowlist** (least privilege at the discovery boundary) + a **trust check** that refuses a tool whose *description* issues instructions to the model (indirect-injection-via-metadata) |

### The raw messages, once (abridged from `handshake.py`)
```
──► initialize            {"method":"initialize","params":{"protocolVersion":"2025-06-18",...}}
◄── initialize result     {"result":{"serverInfo":{"name":"hris-server",...},"capabilities":{...}}}
──► notifications/initialized         (a notification: no id, no reply)
──► tools/list            {"method":"tools/list","params":{}}
◄── tools/list result     {"result":{"tools":[{"name":"get_employee_record","inputSchema":{...}}]}}
──► tools/call            {"method":"tools/call","params":{"name":"get_employee_record",
                                                           "arguments":{"employee_id":"E002"}}}
◄── tools/call result     {"result":{"structuredContent":{"name":"Marcus Reed","jurisdiction":"NA",...}}}
```
That is the entire protocol: **initialize → (initialized) → tools/list → tools/call**, one
JSON object per line over stdio.

---

## 5. Honest framing — what MCP did and did NOT buy us

- **It did not make the agent smarter.** Pass rate is 100% before and after; the tool bodies
  are the *same* `agent_race.tools` functions. MCP changed only the transport (a socket in
  place of a Python import).
- **It bought reuse and swapping.** A third party's agent calls our HRIS server knowing none
  of our code (`external_agent.py`), and we added a whole policy server to our own agent by
  editing a list, not the agent. Those are the two wins, and they are the only two we claim.
- **It moved the trust boundary, so we added guards there.** Tools now cross a process
  boundary from code we may not own, so the client applies least-privilege (an allowlist) and
  refuses tools whose metadata reads like a prompt injection — before the model ever sees them.

---

## 6. Common mistakes — and how this submission avoids them

- **"MCP makes my agent better"** → §5: pass rate is identical; we claim reuse/swapping only.
- **Editing the agent to add MCP** → `agent_race/agent.py` has **0** edits; tools arrive via
  the Week-8 hooks. The proof is `--hris-only` vs default: same binary, different toolset.
- **Reimplementing the tool inside the server** → the servers `import agent_race.tools` and
  call the *real* functions, so the HRIS capability over MCP is byte-identical to in-process.
- **Hiding the protocol behind the SDK forever** → `handshake.py` speaks raw JSON-RPC by hand
  once, so the frames are not a mystery.
- **Trusting any discovered tool** → `safety.py` allowlists tools per server and rejects a
  tool whose description tries to command the model (verified on a crafted malicious tool).
- **Confusing where the AI runs** → §3 diagram + the server that never learns who called it.

---

## 7. Files added this week

`★` = a Week-9 deliverable. Everything under `agent_race/`, `trajectory/`, `eval/`,
`Services/` is the unchanged Week-5→8 foundation (the agent under test is **not** modified).

```
Week9/
├── MCP_RESULTS.md                    ★ this write-up
├── mcp_layer/                        ★ WEEK-9 PACKAGE (the MCP host + servers)
│   ├── servers/
│   │   ├── hris_server.py            ★ OUR server: get_employee_record (the HRIS capability)
│   │   └── policy_server.py          ★ 2nd server: rules + handbook (the "bolt-on" proof)
│   ├── client.py                     ★ host side: connect + DISCOVER + adapt -> (gemini_tools, dispatch)
│   ├── schema_convert.py             ★ MCP JSON-Schema -> Gemini FunctionDeclaration
│   ├── run_mcp_agent.py              ★ THE command: unchanged agent over MCP-discovered tools; --offline
│   ├── handshake.py                  ★ raw JSON-RPC over stdio, by hand, once
│   ├── external_agent.py             ★ "someone else's agent" calling our HRIS server
│   ├── safety.py                     ★ access-control allowlist + tool-trust check
│   └── .mcp_cache*.json              ★ committed run caches -> power --offline with no API key
│
│  ── unchanged foundation (Weeks 5–8) ──────────────────────────────────────────────
├── agent_race/                        Week-7 agent (the loop under test) — 0 edits this week
├── trajectory/  trajectory_eval.py    Week-8 trajectory + injection evals (still reproduce)
├── eval/  Services/  Connection/       Week-5/6 RAG app + eval harness
└── readme.md  requirements.txt  .env   mcp + fastmcp added to requirements
```
