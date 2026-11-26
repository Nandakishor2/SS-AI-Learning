<!-- Soft Suave · The AI Engineering League -->
# Week 9 — Weekly Demo Update

> Plain-language progress update for the weekly demo. No jargon, no hype — just what
> changed, why, and how to show it live.

---

## 1. Previous Week Quick Review
Last week we stopped trusting just the final answer and started grading the *path* the agent
took to get there. We caught the agent being "right for the wrong reason" — guessing the usual
figure without reading the employee — and added a guard that forces it to read the record first.

*Live example:* The agent said "E002 gets 14 weeks" **because** it actually opened E002's record
and matched the band — a correct answer down a correct path.

## 2. What Was the Issue in the Previous Week?
Everything the agent could do was **hand-wired into the agent's own code**. The three tools
(look up an employee, get the rules, search the handbook) were typed straight into the agent.
That means two painful things: no other team can reuse our tools, and every time we want to
add or swap a tool we have to open up and edit the agent itself.

*Live example:* If another team built a great "employee lookup" service, our agent couldn't use
it without us rewriting agent code. And our own tools were trapped inside this one app.

## 3. What Are We Fixing?
We pick up one gap: **our tools are custom-built and locked to this one app, and the agent can
only reach tools we hard-coded into it.** The root cause is that there's no *standard socket*
between an AI and its tools — everyone wires everything by hand, so nothing is reusable.

## 4. What Are We Trying to Fix in This Week?
We adopt **MCP** — think of it as a standard wall socket for AI tools, the way USB is a
standard socket for devices.
- **Step 1 — Expose one of our tools as a standalone server.** We took the employee-lookup
  (the "HRIS" lookup) and wrapped it as a small MCP server that runs on its own. Now anyone's
  agent can plug into it. *Example:* a separate program with zero knowledge of our code asks the
  server "give me E002" and gets the record back.
- **Step 2 — Make the agent *discover* its tools instead of us wiring them in.** On startup the
  agent asks the server "what tools do you have?" and learns them on the spot. We did **not**
  edit the agent to do this. *Example:* the agent boots knowing zero tools and comes back knowing
  three, read off the servers.
- **Step 3 — Bolt on a second tool server without touching the agent.** We added a whole second
  server (the rules + handbook tools) by adding it to a list — not by editing the agent.
  *Example:* same agent, one extra line of setup, two more tools.

## 5. Why Are We Doing It?
Because hand-wiring every tool into every app doesn't scale and can't be reused. With a standard
socket, a tool we build can be used by any AI, and any tool can plug into our agent. **Honest
framing for a client:** MCP does **not** make the AI smarter — it's plumbing. It wins on reuse
and easy swapping, not on better answers. We say that out loud rather than overselling it.

## 6. What Will Be the Results?
The agent now discovers **3 tools over MCP with 0 tools hard-coded in its source**, and still
answers **10 out of 10** correctly — same quality as before, because MCP only changed the
*plumbing*, not the brains. The clearest proof is the swap: run the same agent with only the
employee-lookup server and it scores **0 out of 10** (it can find the person but has no rules
tool), then bolt on the rules server — one line, **no agent edits** — and it jumps back to **10
out of 10**. So the agent's abilities follow the tools it's handed, not code we rewrite.

*Where does the AI actually run?* **On our side, never on the tool server.** The lookup server
is deliberately dumb — it answers "here are my tools" and "here's the result," and never knows
which AI (or whose agent) is asking.

*Before vs After:* **Before** — the agent could only use tools we typed into its code. **After**
— the agent reads its tools off servers at startup, and other people's agents can call ours.

## 7. Live Working Demo Execution Steps
```bash
cd SS-AI-Learning/Week9

# 1. The headline: the UNCHANGED agent, discovering its tools over MCP (offline, no API key)
python3.14 -m mcp_layer.run_mcp_agent --offline
#   -> Point out: "agent received 3 tool(s), none hard-coded in agent.py", 10/10 pass,
#      and "agent_race/agent.py edits: 0".

# 2. The proof — same agent, fewer tools, zero code change
python3.14 -m mcp_layer.run_mcp_agent --hris-only --offline
#   -> Point out: only 1 tool discovered -> 0/10. Bolting on the 2nd server (step 1 above)
#      is what takes it back to 10/10 — and we never touched the agent.

# 3. See the actual messages on the wire, once, so MCP stops being a mystery (needs no key)
python3.14 -m mcp_layer.handshake
#   -> Point out: initialize -> tools/list -> tools/call, one line of JSON each. The server's
#      reply never asks who's calling: the AI runs on OUR side.

# 4. Someone ELSE'S agent calling our HRIS server (imports nothing from our agent)
python3.14 -m mcp_layer.external_agent E002
#   -> Point out: a separate program uses our tool knowing none of our code — that's the reuse.
```
Point out on screen: `mcp_layer/.mcp_cache.json` — the per-question record (tools discovered,
path, pass/fail) so anyone can verify the run offline.

---

### Honest notes for the demo
- **MCP does not improve answer quality** — pass rate is 100% before and after. We claim only
  reuse and swapping, and we say so.
- The servers reuse the **real** Week-7/8 tool code (not a reimplementation), so the lookup over
  MCP is identical to the in-process one — only the transport changed (a socket vs an import).
- Demos 1–2 run **offline from a saved run**, so they work on screen without an API key; a live
  run (`python3.14 -m mcp_layer.run_mcp_agent`) needs `GEMINI_API_KEY` in `.env`. Demos 3–4 use
  no model at all — they're pure MCP — so they always run live.
- Safety: our client only trusts tools on an **allowlist**, and refuses any tool whose
  description tries to give the AI orders (a hidden-instruction attack) — checked in
  `mcp_layer/safety.py`.

---

## 8. One-Question Demo (paste & show) — the actual acceptance criterion

This week the one-question demo is the **MCP agent itself**, so what you show on screen *is* the
Week-9 acceptance criterion — not a foundation stand-in. One question, no cache (live), and it
prints each criterion with its evidence.

```bash
# Ask one question; the agent discovers its tools over MCP and answers through them.
python3.14 -m mcp_layer.run_mcp_agent "Employee E003 is taking primary-caregiver leave. How many weeks of fully paid leave are they entitled to?"
```
**Point at on screen** (the `WEEK-9 ACCEPTANCE CRITERIA` block it prints):
- **[1]** the agent received its tools from the server at runtime — **0 hard-coded** in the agent.
- **[2]** the tools it actually used were **called over MCP** (`get_employee_record`, then
  `get_jurisdiction_rules`) — real `tools/call` round trips, not in-process functions.
- **[3]** each tool is served by a **separate server process**, and **the AI ran on our side**,
  never on the server.
- **[4]** those three tools came from two servers — the second was **bolted on with 0 agent edits**.

And the answer is still correct ("E003 → 18 weeks, HR-208 §2.1"), making the honest point: MCP
changed the *plumbing*, not the answer.

> Needs `GEMINI_API_KEY` in `.env` (it's a live agent run). For a no-key version of the same
> criterion, use `python3.14 -m mcp_layer.run_mcp_agent --offline` (§7).

### Foundation aside — `ask.py` (unchanged, grounding only)
`ask.py` is the Week-5 retrieval assistant, kept as-is. It does **not** demonstrate the Week-9
criterion; it only anchors the demo in the working app's grounding discipline:
```bash
python3.14 ask.py "What's the remote work stipend for APAC engineers?"   # must REFUSE (no such policy)
```
**Point at on screen:** it declines instead of inventing a figure — the same "don't answer what
you didn't ground" discipline our MCP client applies when it refuses a tool whose description
tries to issue instructions.
