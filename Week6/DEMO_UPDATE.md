<!-- Soft Suave · The AI Engineering League -->
# Week 6 — Weekly Demo Update

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
make it cheaper."* Everything below is the detail behind that one screen.

---

## 1. Previous Week Quick Review
Last week (Week 5) we stopped guessing why the HR assistant sometimes gave bad answers and
actually read what it was doing. We saved a full record of 20 real questions — the question,
what it looked up, and what it answered — and read every one by hand. The surprise: the
complaint we were chasing ("it quotes the wrong policy") never actually happened. The real
top problem was the opposite — the assistant *refusing* questions it could easily answer.

*Live example:* An employee asked, "How many weeks of paid parental leave do I get?" and the
assistant replied "I don't have enough information" — even though that exact rule was sitting
right there in the handbook.

## 2. What Was the Issue in the Previous Week?
Here's the catch we hit at the end of Week 5: to decide if an answer is "good" or "bad," our
system uses a second AI to grade the first AI. But nobody had ever checked whether that grader
actually agrees with a human. So every score on our dashboard came from a judge we had never
tested.

*Live example:* The grader looked at a refusal and marked it "PASS." But was that fair? We
genuinely didn't know — we were trusting a number from a machine we'd never checked.

## 3. What Are We Fixing?
This week we pick up that one root problem: **we don't trust the grader yet.** Before we rely
on any score, we have to prove the grader thinks like a human — and if it doesn't, find out
exactly where it disagrees.

## 4. What Are We Trying to Fix in This Week?
- **Step 1 — Build a proper question set.** We gathered 29 real test questions, each tagged
  with the kind of problem it checks, and we replayed 5 of last week's actual failures so they
  can never quietly come back. *Example:* the "parental leave refusal" from Week 5 is now a
  permanent test case.
- **Step 2 — Stop paying the AI to check easy things.** Four checks (like "did it cite a real
  section?" or "is the notice period an actual number?") are simple yes/no rules, so we moved
  those out of the AI grader and into plain code. *Example:* checking that "HR-208 section 2.1"
  is a real section is now a quick lookup, not an AI call.
- **Step 3 — Grade blind, then compare.** We hand-graded 25+ answers *ourselves first* and
  saved them before the AI grader ever ran (the save date proves the order). Then we ran the
  AI grader and measured how often it agreed with us.

## 5. Why Are We Doing It?
Because HR was about to let employees self-serve based on these scores. If the grader is wrong,
we'd be shipping confidence with no backing. A grader you never checked is just a number nobody
should trust. Checking it once means every future change can be measured honestly instead of
argued about.

## 6. What Will Be the Results?
We now have a real agreement figure: the AI grader matches a human **86% of the time**. We also
tried to improve it by feeding it two of its own mistakes as examples — and honestly, it moved
**nothing** (still 86%). More useful: when we read the four disagreements, three of them were
*our* labels being too strict, not the grader being wrong. The real culprit underneath was the
lookup step failing to fetch the right table.

*Before vs After:* **Before** — "the grader says 93% pass, trust it." **After** — "the grader
agrees with a human 86% of the time, here are the exact 4 cases where it doesn't, and the real
bug is in lookup, not the answer."

## 7. Live Working Demo Execution Steps
```bash
cd SS-AI-Learning/Week6

# 1. Run the whole test set in one command (no API key needed)
python3.14 -m eval.run_eval --offline
#   -> Point out: PASS RATE BY MODE, and that "region disambiguation" sits low
#      while easy cases carry the average.

# 2. Show the grader-vs-human agreement, before and after our tweak
python3.14 -m eval.validate_judge --both
#   -> Point out: 86.2% before -> 86.2% after. The tweak didn't help, and we say so.
```
Point out on screen: the file `labels_25.json` was committed *before* the judge ran — that's
our proof we graded blind.

---

## 8. The Demo Scenario — "a hard answer, and the judge confirms it"

**The perfect question (case `C12`) — the same one you run in all three weeks:**
> *"In the UK, if I'm sick for 9 days, what certification do I need and what happens to my pay after the first 4 weeks?"*

This is a genuinely hard, **two-part** question: it needs the right **certification** (a GP Fit
Note, because the absence is 8+ days) *and* the right **pay tiers** (100% for 4 weeks, then 50%
for the next 8). The assistant gets both right. Week 6 is what lets you *trust* that on screen.

### Step 1 — the quality check (prints under every answer, automatically)
```bash
python3.14 ask.py "In the UK, if I'm sick for 9 days, what certification do I need and what happens to my pay after the first 4 weeks?"
```
```
🧪 QUALITY CHECK
   • Refusal     : ANSWER   (substantive answer, not a refusal)
   • Citations A1: [PASS] all citations resolve (HR-209/UK§2.1, HR-209/UK§2.1)
   LLM judge (v2): ✅ PASS   reason: correct certification and pay structure per the policy
```
**Point at on screen:** the deterministic check `A1` proves — for **free, no model call** — that
every `[Chunk … Section …]` citation points to a section that really exists; then the judge
confirms the substance is right. Trustworthy, and you can see *why*.

### Step 2 — Human vs Judge v1 vs Judge v2 (reproducible, verified 4/4)
```bash
python3.14 ask.py --both-judges "In the UK, if I'm sick for 9 days, what certification do I need and what happens to my pay after the first 4 weeks?"
```
```
🟩 WEEK 6 · JUDGE v1  vs  JUDGE v2
   👤 HUMAN label [C12]: PASS      ← the ground truth
   ⚖️  Judge v1: ✅ PASS
   ⚖️  Judge v2: ✅ PASS
   → v1 and v2 agree (PASS) here — the iteration changed nothing on this case.
```
All three agree: the human who hand-labelled it, and both judge versions. **That is the 86%
agreement in action** — on a case everyone gets right. (`--both-judges` grades the *frozen*
evaluation answer for `C12`, so it's identical every run.)

### Step 3 — but WHY check a judge at all? (show a disagreement)
A judge that only ever agrees isn't worth checking. The *point* of Week 6 is the cases where the
human and the judge **disagree**. The clean one is a false refusal (case `C03`):
```bash
python3.14 ask.py --both-judges "What paid leave does a primary caregiver with 2 years of service get in North America under HR-208?"
```
```
   👤 HUMAN label [C03]: FAIL     ← human: "answerable — 14 weeks IS in the handbook"
   ⚖️  Judge v1: ✅ PASS           ← judge: "the retrieved context lacks the figure; refusing is correct"
   ⚖️  Judge v2: ✅ PASS
```
Here the human **rejects** the refusal (answerable in principle) but **both judges pass** it
(correct for what retrieval actually fetched). That gap — the human disagreeing ~14% of the time —
is exactly why you validate a judge before trusting its score. *(We also report the honest v1→v2
finding: the iteration didn't move the aggregate, `86.2% → 86.2%`.)*

### Step 4 — the trainer's "but the answer IS 14 weeks — why can't it find it?" (retrieval proof)
```bash
python3.14 ask.py --validate "What paid leave does a primary caregiver with 2 years of service get in North America under HR-208?"
```
```
🔬 VALIDATION — is the answer actually in the corpus?
   PRODUCTION retrieval (top_k=3):  REFUSED ❌   sources: [NA_2, NA_4, NA_1]
   DEEPER retrieval     (top_k=10): ANSWERED ✅  "... 14 weeks ... [Chunk: struct_HR-208_NA_3 ... §2.1]"
   Answer-bearing chunk below the top-3 cutoff:  • rank 7: struct_HR-208_NA_3 (HR-208/NA)
   → The figure was in the corpus all along; top_k=3 ranked it out. Retrieval gap, not missing data.
```
The chunk holding "14 weeks" (`NA_3`) doesn't contain the words "primary caregiver" (those are in
the heading chunk `NA_2`), so retrieval ranks it out. The fix is section-aware chunking — the bug
is upstream in retrieval, not the model or the judge.

### Usage (Week 6 only)
Every Week-6 answer prints a **🟦 WEEK 6 USAGE** block — Week 6 makes two calls per question (the
answer, and the judge that grades it):
```
1) answer call : ~1,110 tok  $0.0013
2) judge call  : ~2,000 tok  $0.0020
TOTAL          : ~3,110 tok  $0.0033
```

---
Flags:
```bash
python3.14 ask.py --both-judges "...<question>..."       # Human vs Judge v1 vs Judge v2, side by side
python3.14 ask.py --no-judge "...<question>..."          # free deterministic checks only, no model call
python3.14 ask.py --validate "...<question>..."          # prove a refusal is a retrieval gap (top_k=3 vs 10)
```
> Each live judge is one Gemini call; `--both-judges` makes two, `--validate` adds two more. The
> offline, graded-against-labels view (`eval.validate_judge --both`, 86% human agreement) is the
> source of truth.
