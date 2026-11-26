<!-- Soft Suave · The AI Engineering League -->
# Week 5 — Weekly Demo Update

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
| **6** 🟩 | *(identical answer)* | **🧪 QUALITY CHECK** → citations resolve (`A1 PASS`) and `Judge: ✅ PASS`. `--both-judges` shows **Human PASS · Judge v1 PASS · Judge v2 PASS** — the validated grader (86% human agreement) confirms it. |
| **7** 🟦 | *(identical answer)* | **💰 TOKEN / COST** → `~1,070 tok · $0.0012`, and `--compare` proves a roundabout agent costs **~3× more** for the same answer. |

**Say this out loud:** *"Same assistant, same correct answer. Week 5 could only answer. Week 6
can tell me whether that answer is trustworthy. Week 7 can tell me what it costs — and how to
make it cheaper."*

---

## 1. What Week 5 Is
Week 5 is the **baseline and the diagnosis**. We stopped guessing why the HR assistant sometimes
gave bad answers and actually read what it was doing: we saved full traces of real questions —
the question, what it retrieved, and what it answered — and read every one by hand, then ranked
the failure types into a taxonomy.

*The headline finding:* the complaint we were chasing ("it quotes the wrong policy") barely
happened. The **#1 real problem was the opposite — the assistant *refusing* questions it should
be able to answer** (a "false refusal").

## 2. The Perfect Question (the baseline, live)
> *"In the UK, if I'm sick for 9 days, what certification do I need and what happens to my pay after the first 4 weeks?"*

```bash
cd SS-AI-Learning/Week5
python3.14 ask.py "In the UK, if I'm sick for 9 days, what certification do I need and what happens to my pay after the first 4 weeks?"
```
**What prints:** the retrieved UK sources, then a correct **two-part** answer — *GP Fit Note*, and
*100% pay for 4 weeks then 50% for the next 8 weeks* [HR-209/UK §2.1] — then the 🟫 **WEEK 5 ·
BASELINE** marker:
```
🟫 WEEK 5 · BASELINE — answer only.
   ❓ Is this answer trustworthy?  → unknown (no grader) ...... added in WEEK 6
   ❓ What did this answer cost?    → unknown (no metering) .... added in WEEK 7
```
**Point at on screen:** the baseline handles a genuinely hard, two-part question (the right
certification **and** the pay tiers) and gets it right. But in Week 5 we have **no way to confirm
it's right and no idea what it cost** — we're trusting it on faith. Those two blind spots are
exactly what Weeks 6 and 7 close.

## 3. How to Show the Diagnosis Work
```bash
# The hand-read traces and the ranked failure taxonomy (the Week-5 deliverables)
python3.14 run_week5.py
#   -> Point out: we read every trace by hand and ranked the failure types. The
#      #1 failure class was "false refusal" (it refuses answerable questions) —
#      the opposite of the complaint we were chasing.
```
Point out on screen: `taxonomy.md` (the ranked failure modes) and `golden_set.jsonl` (the saved
real cases) — the evidence base. The perfect question above is a case the baseline gets *right*;
the taxonomy is where we catalogue the cases it gets *wrong*. Week 5 can't yet tell the two apart
automatically — that's the gap Week 6 fills.

---
> This question is the project's own `clean_grounded` case `C12`. In Week 6 the validated judge
> (and both judge versions) **confirm** it — Human PASS · Judge v1 PASS · Judge v2 PASS — and in
> Week 7 it carries the token/cost panel. One question, three weeks, three lessons.
