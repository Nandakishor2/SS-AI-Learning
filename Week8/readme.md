<!-- Soft Suave · The AI Engineering League -->
# Week 8 — Agent Failure Modes & Trajectory Evals

> **Scope:** Week 8 · Module M4 (Agents). A direct extension of the Week-7 HR agent.
> Week 7 asked *"does this task even need an agent?"*; **Week 8 asks *"the agent passes
> its outcome eval and HR still doesn't trust it — is it reaching right answers down wrong
> paths, and can it be tricked?"*** We grade the **trajectory** (the whole path), not just
> the final answer.

The headline is the **outcome-vs-trajectory gap**: the agent can state the right figure
*without ever reading the employee's record* — right by luck on the common case, wrong
everywhere else. The eval exposes it as a number; one mitigation closes it, with the price
measured.

---

## 1. Headline results

| metric (same 10 HR cases) | v0 control | v1 baseline | v2 mitigated |
|---|---:|---:|---:|
| tool-choice accuracy | 100% | **0%** | 80% |
| argument validity rate | 100% | 100% | 100% |
| step efficiency (taken/needed) | 1.05 | 0.50 | 1.30 |
| cost/question p50 · MAX | $0.00162 · $0.00195 | $0.00072 · $0.00077 | $0.00234 · $0.00314 |
| outcome pass rate | 100% | **20%** | 80% |
| trajectory pass rate | 100% | **0%** | 80% |

- **Gap (v1): 20 points** (20% outcome − 0% trajectory). Right-answer-wrong-path cases:
  **Q01, Q07** — both answered from a fast-path cache, never reading the employee.
- **Mitigation** (a record-first guard): top mode `skipped_lookup` **10 → 2**, outcome
  **20% → 80%**, at a price of **+18,851 tokens / 10 q** and **+4,439 ms** p50 latency.

Full write-up and the disagreement/residual analysis: [`TRAJECTORY_RESULTS.md`](TRAJECTORY_RESULTS.md).
Per-question record: [`trajectory/trajectory_eval.csv`](trajectory/trajectory_eval.csv).

> Numbers are one real live run against `gemini-2.5-flash`, cached in
> `trajectory/.traj_cache_*.json` so a grader reproduces the whole table with **no API key**:
> `python3.14 trajectory_eval.py --offline`.

---

## 2. The commands

> Needs `.env` with `GEMINI_API_KEY`. Use `python3.14`. The eval is self-contained —
> **no Docker / no Qdrant / no ingest** (the agent runs over a local index, as in Week 7).

```bash
# THE TRAJECTORY EVAL — the four numbers, the gap, the mitigation, the regression table
python3.14 trajectory_eval.py                 # live (runs v0/v1/v2, refreshes caches)
python3.14 trajectory_eval.py --offline       # reproduce the whole report from cache, no API

# Capture one variant's raw trajectories alone
python3.14 -m trajectory.capture v1_baseline  # v0_control | v1_baseline | v2_mitigated

# BONUS — indirect prompt injection: attack -> defend -> re-attack -> residual
python3.14 -m trajectory.injection
python3.14 -m trajectory.injection --offline
```

---

## 3. How each Week-8 requirement is met

| # | Requirement | Where |
|---|---|---|
| 1 | Expected tool sequences for 10 cases; alternate valid paths asserted as a **set** | [`trajectory/expected.py`](trajectory/expected.py) — record-first, handbook before/after/instead accepted |
| 2 | Four trajectory numbers (tool-choice, argument validity, step efficiency, cost **p50 & max**) | [`trajectory/score.py`](trajectory/score.py) + `trajectory_eval.py` |
| 3 | Outcome-vs-trajectory **gap** as a number + one right-answer-wrong-path case with its path | §3 of `TRAJECTORY_RESULTS.md` (Q01/Q07, 20 pts) |
| 4 | Exactly **ONE** mitigation to the top mode; before→after + the **price** as a number | `record_first_guard` in [`trajectory/variants.py`](trajectory/variants.py); `skipped_lookup` 10→2 |
| 5 | Regression check: per-mode counts before/after, naming any mode worse/new | §5 of `TRAJECTORY_RESULTS.md` (none worse; residual `skipped_lookup` named) |
| Bonus | Indirect injection, attacked then defended; what still gets through + cost | [`trajectory/injection.py`](trajectory/injection.py) |

### Why a seeded regression — stated honestly
The vanilla Week-7 agent is **already clean**: probing it (even with vague descriptions and a
free-text jurisdiction) shows it always reads the record first and passes a legal
jurisdiction — so `v0_control` scores 100%/100% and there is **no natural gap**. A trajectory
eval you cannot trip teaches nothing (the Week-6 lesson: validate your instrument). So we
reproduce the **real, common production regression** the task is about — a latency-minded
engineer bolts on a `get_quick_entitlement` fast-path cache and a prompt that prefers it —
and show the eval catches what that "optimization" costs. The fix is a **mechanism** (the
guard), never a prompt revert.

---

## 4. The failure zoo (`trajectory/score.py`)

Each trajectory is classified into exactly one mode:

| mode | what it means |
|---|---|
| `clean` | accepted path, real args, answered — trajectory PASS |
| `skipped_lookup` | answered the entitlement **without reading the employee record** (the headline bug) |
| `wrong_tool_order` | fetched the numbers **before** the record (jurisdiction guessed) |
| `guessed_jurisdiction` | read the record, but a rules/handbook arg was fiction / mismatched |
| `off_path` | right tools, but a shape outside the accepted set |
| `redundant_steps` | clean path but ≥ 2× the needed steps (thrash / loop) |
| `budget_terminated` | hit a budget and stopped (spun) |

---

## 5. Files — complete structure & purpose

`★` = a Week-8 graded deliverable. The `trajectory/` package is **this week's work**;
`agent_race/` (and `eval/`) below the divider are the Week-5/6/7 app and harness reused
unchanged except for three backward-compatible hooks on `run_agent` (custom prompt, tool
set, and a per-call `guard`).

```
Week8/
│
├── trajectory_eval.py              ★ THE one command: four numbers + gap + mitigation
│                                     before→after + per-mode regression table; --offline
├── TRAJECTORY_RESULTS.md           ★ the write-up: numbers, the gap, the two RAWP cases,
│                                     the mitigation & its price, the regression, the bonus
├── trajectory/                     ★ WEEK-8 PACKAGE (trajectory evals)
│   ├── expected.py                 ★ the 10 expected tool sequences (accepted as a SET)
│   ├── score.py                    ★ per-trajectory scoring + the failure-zoo classifier
│   ├── variants.py                 ★ v0 control / v1 fast-path regression / v2 + guard;
│   │                                 the fast-path tool and the record-first MITIGATION
│   ├── capture.py                    runs one variant over the 10 Qs, caches trajectories
│   ├── injection.py                ★ BONUS: indirect prompt injection attack + defence
│   ├── trajectory_eval.csv         ★ per-question record (path, modes, pass/fail, cost)
│   ├── trajectory_report.json        machine-readable summary of the run
│   ├── .traj_cache_v{0,1,2}*.json     cached live trajectories -> power --offline replay
│   └── .injection_cache.json          cached injection transcript
│
│  ── Week-7 foundation (the agent UNDER TEST; reused) ────────────────────────────
├── agent_race/                       Week-7 agent vs workflow package; agent.py is the
│   │                                 loop the trajectory eval drives (now with 3 optional
│   │                                 hooks: system_prompt, gemini_tools, guard, dispatch)
│   ├── agent.py  tools.py  questions.py  scoring.py  llm.py  workflow.py  race.py …
│   └── data/                         employees / jurisdiction_rules / handbook (local index)
├── VERDICT.md  TOOL_DIFF.md          Week-7 graded deliverables (agent-vs-workflow race)
├── RESULTS.md                        Week-6 eval write-up (kept as foundation)
│
│  ── Week-5/6 foundation (unchanged) ────────────────────────────────────────────
├── eval/                             Week-6 eval harness (run_eval, judge, assertions)
├── taxonomy.md  labels_25.json  judge_v*.txt  prediction.txt  agreement_*.txt
├── Services/  ask.py  Connection/    Week-5 RAG app
├── INSTALLATION.md  requirements.txt  .env  .gitignore
└── readme.md                         this file
```

---

## 6. Common mistakes — and how this submission avoids them

- **Reporting the outcome eval only** → the gap (§3) is the headline; Q01/Q07 pass the
  answer check and fail the path check, and we show the path.
- **Over-asserting one exact tool sequence** → `expected.py` accepts the handbook
  before/after/instead as a **set**; a correct non-canonical run is not a false failure.
- **Shipping two mitigations at once** → exactly one change (the guard); v1 and v2 differ
  in that mechanism alone, so the before→after is attributable.
- **Calling the mitigation free** → its price is three real numbers: +18,851 tokens,
  +$0.00162 cost/q p50, +4,439 ms p50 latency.
- **Reporting mean cost** → cost is p50 **and** max; the mean would bury the re-plan spread.
- **Fixing injection with a prompt** → defence is least-privilege (no write tool) +
  sanitised read-only output + an output guardrail, and we name what still gets through.

---

## 7. Foundation (unchanged Week-5/6/7 app)

6 regional leave-policy PDFs → structure-aware chunks in Qdrant → hybrid retrieval → Gemini
2.5 Flash grounded generation (Weeks 5–6); the Week-7 agent answers entitlement questions
over a local `employees / jurisdiction_rules / handbook` index with three tools. Week 8 adds
only the trajectory eval and the injection harness on top; the agent's own tool behaviour is
untouched.
