<!-- Soft Suave · The AI Engineering League -->
# Week 7 — Race the HR agent against a fixed workflow

> **Scope:** Week 7 · Module M4 (Agents). A direct extension of the HR-policy app.
> The question this week: *the entitlement task runs fine as an agent loop — but does it
> **need** to be an agent, or would three hard-coded steps be faster, cheaper and more
> auditable?* We settle it with **four numbers per system**, not an opinion.

The headline is the **race table**: the same agent task re-implemented as a fixed workflow,
run over the **same 10 employee questions**, compared on pass rate, p50 latency, tokens, and
cost per question.

---

## 1. Headline results — the race (8 numbers)

| metric | AGENT (loop) | WORKFLOW (fixed) |
|---|---|---|
| pass rate | 100% (10/10) | 100% (10/10) |
| p50 latency | 4404 ms | **1740 ms** |
| total tokens (10 q) | 24,792 | **6,244** |
| cost / question | $0.001630 | **$0.000695** |

Agent costs **~2.3×** and runs **~2.5×** slower for the **same** pass rate. 8 of the 10
questions branch on tenure/probation, yet the branch is a *fixed* shape, so hard-coded `if`
beats the loop on every number. Full verdict: [`VERDICT.md`](VERDICT.md). Per-question
breakdown: [`agent_race/race.csv`](agent_race/race.csv).

> Numbers are a real live run against `gemini-2.5-flash`, cached in
> `agent_race/.race_cache.json` so a grader can reproduce the table with **no API key**:
> `python3.14 -m agent_race.race --offline`.

---

## 2. The commands (one each)

> Needs `.env` with `GEMINI_API_KEY`. Use `python3.14`. The race is self-contained —
> **no Docker / no Qdrant / no ingest** (the handbook is a local index, see §5).

```bash
# THE RACE — both systems over the same 10 questions -> race.csv + the 8-number table
python3.14 -m agent_race.race                 # live
python3.14 -m agent_race.race --offline       # reproduce the table from cache, no API

# Each system runnable ALONE (one command each)
python3.14 -m agent_race.agent                # agent loop over all 10
python3.14 -m agent_race.workflow             # fixed workflow over all 10
python3.14 -m agent_race.agent "Employee E002 is taking primary-caregiver leave. How many weeks of fully paid leave are they entitled to?"

# Budget-termination demo — forces a clean stop, writes logs/budget_termination.log
python3.14 -m agent_race.agent --demo-budget

# Bonus — sliding window + summarisation + persistence across restart, on 3 long convos
python3.14 -m agent_race.conversation
```

---

## 3. How each Week-7 requirement is met

| # | Requirement | Where |
|---|---|---|
| 1 | Third tool: one job, enum param, no description overlap | `agent_race/tools.py` → `get_jurisdiction_rules` (enum jurisdiction); diff in [`TOOL_DIFF.md`](TOOL_DIFF.md) |
| 2 | Re-implement the task as a fixed workflow — same tools/model/output, no loop | `agent_race/workflow.py` (3 hard-coded steps, exactly one model call) |
| 3 | Race over the same 10 Qs (≥3 input-branching), 4 numbers each | `agent_race/race.py` → `race.csv`; 8 of 10 branch (`questions.py`) |
| 4 | All four budgets enforced + a clean budget-termination log | `agent_race/agent.py` (iters/tokens/cost/wall-clock checked every lap); `agent_race/logs/budget_termination.log` |
| 5 | Verdict applying the decision rule, consistent with the numbers | [`VERDICT.md`](VERDICT.md) |
| Bonus | Sliding window + summarisation + persist across restart; name a destroyed detail | `agent_race/conversation.py` |

### The four budgets (all checked every lap, in `agent.py`)
`MAX_ITERS=6` · `MAX_TOKENS=20000` · `MAX_COST_USD=0.02` · `WALL_CLOCK_S=30`.
Each is tested **before** spending another model call; whichever trips first sets
`stop_reason` and the loop returns cleanly. The demo tightens `MAX_ITERS=2` and logs the
fire:

```
STOP_REASON: budget:max_iters   <-- budget that fired
laps_used: 2/2   tokens_used: 1436   cost_used: $0.000902
Loop terminated cleanly on the budget — it did NOT spin.
```

### Why tokens are summed per lap (not just the last call)
The loop re-sends the whole growing message list every lap, so a question's token bill is
the **sum over laps**. `llm.Meter.add()` accumulates `usage_metadata` on *every* call —
counting only the final call would understate the agent by ~4× (6,244 → the real 24,792).

---

## 4. The 10 questions & the branch

Each names an employee by id but **not** their jurisdiction or tenure — those are discovered
from the record, which is what forces the lookup→rules→branch path. `branching=True` means
step 3 depends on what step 2 found (the entitlement figure is picked by the employee's
tenure/probation band). See `agent_race/questions.py`.

| cases | class | branches on |
|---|---|---|
| Q01–Q03 | NA primary-caregiver leave | tenure band (<12 / 12–36 / >36 mo → 8 / 14 / 18 weeks) |
| Q04–Q05 | LATAM primary-caregiver leave | tenure band (<6 / 6+ mo → 6 / 12 weeks) |
| Q06–Q08 | APAC/EMEA carry-over cap | probation vs confirmed (→ 3 / 10 / 5 days) |
| Q09 | UK sick certification | absence duration (10 days → GP Fit Note) |
| Q10 | ANZ personal leave | service year (Year 2+ → 12 days) |

---

## 5. Files — complete structure & purpose

`★` = a Week-7 graded deliverable. The `agent_race/` package is **this week's work**;
everything below the divider is the Week-5/6 app and evals left in place, unchanged.

```
Week7/
│
├── agent_race/                     ★ WEEK-7 PACKAGE (agent vs workflow race)
│   ├── agent.py                    ★ the AGENT: tool-calling loop; enforces all 4 budgets
│   │                                 every lap; `--demo-budget` writes the termination log
│   ├── workflow.py                 ★ the FIXED WORKFLOW: 3 hard-coded steps, same tools +
│   │                                 model + output contract, ONE model call, no loop
│   ├── race.py                     ★ runs both over the 10 Qs → race.csv + the 8-number
│   │                                 table; `--offline` replays the cache (no API)
│   ├── tools.py                    ★ the 3 tools + Gemini function schemas + jurisdiction
│   │                                 enum; sharpened, non-overlapping descriptions
│   ├── questions.py                   the 10 employee questions + expected figures + the
│   │                                  shared system prompt / output contract
│   ├── scoring.py                     deterministic pass gate (figure+unit & policy id);
│   │                                  no LLM judge in the pass decision
│   ├── llm.py                         shared Gemini call wrapper + Meter (per-lap token &
│   │                                  cost accounting, pricing constants)
│   ├── conversation.py             ★ BONUS: sliding window + summarisation + persist
│   │                                  jurisdiction across a simulated process restart
│   ├── data/
│   │   ├── employees.json             10 employee records (jurisdiction, tier, hire_date)
│   │   ├── jurisdiction_rules.json    structured leave numbers/bands per jurisdiction
│   │   └── handbook.json              free-text passages search_handbook() searches locally
│   ├── logs/
│   │   └── budget_termination.log  ★ log of the run that hit a budget and stopped cleanly
│   ├── race.csv                    ★ per-question results (8 numbers over the 10 Qs)
│   ├── race_summary.json              machine-readable 8-number summary
│   └── .race_cache.json               cached live answers → powers `--offline` reproduction
│
├── TOOL_DIFF.md                    ★ third tool's description diff + enum + overlap check
├── VERDICT.md                      ★ the verdict paragraph (<150 words), matches the table
│
│  ── Week-5/6 app underneath (unchanged; the tools reuse its domain data) ─────────
├── data_drop/                         the 7 regional HR policy PDFs (source of the rules)
├── Services/                          Week-5 RAG app (ingest, retrievers, rag_engine)
├── eval/                              Week-6 eval harness (run_eval, judge, assertions)
├── Connection/gemini.py               original Gemini connection smoke-test
├── ask.py                             Week-5 interactive RAG CLI entrypoint
├── RESULTS.md / taxonomy.md / labels_25.json / judge_v*.txt / prediction.txt /
│   agreement_*.txt                    Week-6 graded deliverables (kept for reproducibility)
├── INSTALLATION.md                    environment setup (Qdrant is only needed for Week 5/6)
├── requirements.txt                   deps (google-genai, qdrant-client, …)
└── readme.md                          this file
```

---

## 6. The verdict (one line; full in `VERDICT.md`)

The path varies by **value** (tenure bands) but not by **shape** (always lookup → rules →
branch), so hard-coded steps win on all four numbers at equal accuracy. **None of the 10
forces an agent.** The class that would is **open-ended multi-hop**, where the number of
lookups is unknown until intermediate results are read — only then does the loop earn its cost.

---

## 7. Common mistakes — and how this submission avoids them

- **Racing on single-lookup questions the agent trivially wins** → 8 of 10 questions branch
  on tenure/probation (`questions.py`), so the input mix includes the branching cases.
- **Counting only the final call's tokens** → `Meter.add()` sums `usage_metadata` every lap.
- **Declaring budgets but not checking them** → all four are tested every lap in `agent.py`,
  with a log proving a clean fire.
- **Fixing tool thrash via the system prompt** → fixed by sharpening the tool *descriptions*
  (`TOOL_DIFF.md`), not by bolting "use the right tool" onto the prompt.
- **A verdict that contradicts the table** → `VERDICT.md` ships the workflow, matching the
  numbers (workflow ahead on latency/tokens/cost, tied on pass rate).
