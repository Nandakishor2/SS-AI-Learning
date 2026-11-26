<!-- Soft Suave · The AI Engineering League -->
# Week 7 — Weekly Demo Update

> Plain-language progress update for the weekly demo. No jargon, no hype — just what
> changed, why, and how to show it live.

---

## 0. The actual Week 5 → 6 → 7 difference (show this FIRST, right after the overview)

Run the **same question** in all three folders. The answer is **identical** every time — a
correct, two-part answer. What changes is what each week can *tell you* about that answer. That
escalation is the whole project in one screen.

```bash
Q="In the UK, if I'm sick for 9 days, what certification do I need and what happens to my pay after the first 4 weeks?"
cd SS-AI-Learning/Week5 && python3.14 ask.py "$Q"   # 🟫 baseline
cd SS-AI-Learning/Week6 && python3.14 ask.py "$Q"   # 🟩 + validated judge
cd SS-AI-Learning/Week7 && python3.14 ask.py "$Q"   # 🟦 + token/cost
```

| Week | The answer (same every time) | What that week **adds on screen** |
|---|---|---|
| **5** 🟫 | *"GP Fit Note; 100% pay for 4 weeks, then 50% for 8 weeks"* [HR-209/UK §2.1] | **Nothing but the answer.** It even prints `trustworthy? unknown · cost? unknown`. You can't tell if the answer is right, or what it cost. |
| **6** 🟩 | *(identical answer)* | **🧪 QUALITY CHECK** → `Judge: ✅ PASS`; `--both-judges` shows **Human PASS · Judge v1 PASS · Judge v2 PASS** — the validated grader confirms it. |
| **7** 🟦 | *(identical answer)* | **💰 TOKEN / COST** → `~1,070 tok · $0.0012`, and `--compare` proves a roundabout agent costs **~3× more** for the same answer. |

**Week 7's before/after lives inside Week 7:** `--compare` answers the *same* question two ways —
a roundabout agent (`3,543 tok`) vs the direct workflow (`1,067 tok`), ~3× cheaper for the same
answer. (See §8.)

**Say this out loud:** *"Same assistant, same correct answer. Week 5 could only answer. Week 6 can
tell me whether that answer is trustworthy. Week 7 can tell me what it costs — and how to make it
cheaper."* Everything below is the Week-7 detail behind the 🟦 panel.

---

## 1. Previous Week Quick Review
Last week we proved our answer-grader roughly agrees with a human (86%), so now we can measure
changes with a real number instead of a gut feeling. With a trustworthy grader in hand, we
turned to the assistant itself and asked a bigger question about how it's built.

*Live example:* We could now take an answer like "E002 gets 14 weeks, per HR-208" and get a
fair, checked PASS/FAIL on it — the measuring stick was finally reliable.

## 2. What Was the Issue in the Previous Week?
Our assistant is an "agent" — it decides its own steps each time: look up the employee, read
the rules, pick the number. It works, but it's slow and pricey because it re-reads everything
at each step and thinks out loud a lot. Nobody had checked whether this job even *needs* that
freedom.

*Live example:* Ask "How many days can E006 carry over?" and the agent takes ~4.4 seconds and
burns a big pile of tokens — for a question that's really just three fixed steps every single
time.

## 3. What Are We Fixing?
We pick up one honest question: **do we need an agent for this at all, or would a plain fixed
checklist do the same job cheaper?** The root issue is cost and speed we might be paying for
nothing.

## 4. What Are We Trying to Fix in This Week?
- **Step 1 — Build the boring version.** We re-did the exact same task as a hard-coded
  checklist (look up employee → get rules → pick the band), no free-thinking loop. *Example:*
  for E006 it runs the same three steps in fixed order every time.
- **Step 2 — Race them fairly.** We ran the agent and the checklist over the *same 10 employee
  questions* and measured four things each: did it get the right answer, how fast, how many
  tokens, how much money.
- **Step 3 — Put safety rails on the agent.** We added limits (max steps, max tokens, max cost,
  max time) so the agent stops cleanly instead of spinning forever, and saved a log proving one
  clean stop. *Example:* with a tight 2-step limit, it halts and says "stopped: hit the step
  budget" instead of looping.

## 5. Why Are We Doing It?
Because "use an agent" is the fashionable answer, and fashion costs money in production. If
every HR question quietly costs 2–3× more and runs slower for no gain, that bill grows every
day nobody checks it. Measuring it once tells us where to spend the agent's power and where a
cheap checklist is the honest choice.

## 6. What Will Be the Results?
Both get the right answer on all 10 (100% each). But the checklist is **~2.5× faster** (1.74s
vs 4.4s) and **~2.3× cheaper** ($0.0007 vs $0.0016 per question), using about a quarter of the
tokens. Verdict: ship the checklist for this task — none of these 10 questions actually needs
an agent. An agent only earns its keep when you don't know the steps ahead of time.

*Before vs After:* **Before** — "E006 → 3 days" in 4.4s costing $0.0016. **After** — same
"E006 → 3 days" in 1.7s costing $0.0007. Same answer, less than half the cost.

## 7. Live Working Demo Execution Steps
```bash
cd SS-AI-Learning/Week7

# 1. Run the head-to-head race (offline, no API key)
python3.14 -m agent_race.race --offline
#   -> Point out the table: pass rate 100% vs 100%, but workflow wins on
#      latency, tokens, and cost per question.

# 2. Show the agent stopping cleanly on a budget instead of spinning
python3.14 -m agent_race.agent --demo-budget
#   -> Point out: "STOP_REASON: budget:max_iters" — it halted on purpose.
```
Point out on screen: `VERDICT.md` — the written decision ("ship the workflow") matches the
numbers in the table.

---

## 8. One-Question `ask.py` Demo (paste & show)
`ask.py` prints the sources, the cited answer, **and now a `💰 TOKEN / COST` panel** — the
token/cost math from the race, moved into the path a person actually types into. Until this
week `ask.py` threw the usage numbers away; now every answer shows exactly what it cost.

We use the **same** UK sick-leave question that Weeks 5 and 6 answer, so one question threads all
three weeks: Week 5 answers it, Week 6 grades it, Week 7 prices it.

```bash
# Default: one grounded answer + its real token/cost.
python3.14 ask.py "In the UK, if I'm sick for 9 days, what certification do I need and what happens to my pay after the first 4 weeks?"
#   -> Answer: GP Fit Note; 100% pay for 4 weeks, then 50% for 8 weeks [HR-209/UK §2.1]
#   -> 💰 TOKEN / COST [direct workflow — 1 call]: 1 call | ~1,067 tok | ~$0.0012
```
**Point at on screen:** one retrieval, one cited answer, and a real dollar figure under it —
no hand-waving about cost.

Then the headline: answer the **same** question two ways and watch the reduction, measured live:
```bash
python3.14 ask.py --compare "In the UK, if I'm sick for 9 days, what certification do I need and what happens to my pay after the first 4 weeks?"
```
**Point at on screen — the `💰 COST COMPARISON` table:**
```
   strategy                   calls    tokens      cost $
   roundabout agent (before)      3     3,543    0.003743
   direct workflow (after)        1     1,067    0.001216
   reduction: 70% fewer tokens, 68% cheaper (agent costs 3.3x per answer)
```
Same grounded answer either way — the roundabout version (draft → self-critique → finalise)
just re-sends the whole policy context every lap and re-pays for it. That is Week 7's lesson
on the exact question a viewer typed: **adaptability the task never needed is pure cost.**

> `--compare` makes 4 live calls (3 + 1), so it costs ~4× a normal ask — it's a demo switch.
> Numbers wobble run-to-run (temp 0 still varies length); the *direction* (agent several×
> dearer, same answer) is the reproducible part. The formal 10-question race is still
> `python3.14 -m agent_race.race --offline` (both 100%, workflow 24,792 → 6,244 tokens).
