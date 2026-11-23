<!-- Soft Suave · The AI Engineering League -->
# Week 6 — Results: validating the policy-answer judge

## 0. The numbers

| | |
|---|---|
| Eval cases (mode-tagged) | **29** (≥25) |
| Regression cases (verbatim replays of failed Week-5 traces) | **5** — C01, C17, C20, C22, C27 |
| Deterministic assertions **vs** judged criteria | **4 vs 1** |
| Judge↔human agreement **before** (judge v1) | **86.2 % (25/29)** |
| Judge↔human agreement **after** (judge v2) | **86.2 % (25/29)** |
| Delta | **+0.0 pts** |
| Prediction | **WRONG** (iteration moved nothing) — scored in §4 |

Blind-protocol proof (commit order):

```
commit c194415  Week 6: eval harness + BLIND hand-labels, committed BEFORE any judge run
commit 505e97d  Week 6: run judge v1 (agreement 86.2%) + prediction written BEFORE iterating
```

`labels_25.json` is in commit **1**; the judge's first run and all verdicts are in
commit **2** and later. The judge could not have influenced the labels — the labels
physically predate it in git. (`labels_25.json` also pins `answers_sha256` of the
frozen answer snapshot it was written against.)

---

## 1. Pass rate by mode

Two views of the same 29 answers. **This is the whole point of validating the judge:**
the eval's pass-rate-by-mode is only as trustworthy as the judge that scores it.

### 1a. As the one command prints it (`run_eval`, judge-scored)
A case PASSES iff **all applicable assertions pass AND the judge says PASS**.

| Mode | pass/total | rate | failing |
|---|---:|---:|---|
| M1_false_refusal | 3/3 | 100 % | – |
| M2_region_disambiguation | 1/3 | **33 %** | C18, C19 |
| M3_tenure_boundary | 2/2 | 100 % | – |
| M4_multi_region | 2/2 | 100 % | – |
| M5_date_provenance | 2/2 | 100 % | – |
| clean_grounded | 13/13 | 100 % | – |
| clean_refusal | 4/4 | 100 % | – |
| **OVERALL** | **27/29** | **93.1 %** | C18, C19 |

### 1b. By the stricter blind human labels (ground truth)
If instead we score each case by the human's blind correctness label:

| Mode | pass/total | rate |
|---|---:|---:|
| M1_false_refusal | 1/3 | 33 % |
| M2_region_disambiguation | 0/3 | **0 %** |
| M3_tenure_boundary | 1/2 | 50 % |
| M4_multi_region | 2/2 | 100 % |
| M5_date_provenance | 2/2 | 100 % |
| clean_grounded | 13/13 | 100 % |
| clean_refusal | 4/4 | 100 % |
| **OVERALL** | **23/29** | **79.3 %** |

> **Two things are hidden here.**
> 1. Within either view the easy `clean_grounded` mode (13 cases, 100 %) carries the
>    average and masks the floor (`M2` at 33 % / 0 %) — the Week-6 common mistake.
> 2. The **gap between the two views** (93 % vs 79 %) is exactly the 4 judge↔human
>    disagreements (C02, C03, C17 where the judge says PASS and the human says FAIL,
>    plus C22). The judge-scored mode table is rosier *because the judge is lenient on
>    precisely the disputed cases* — which is why §3–4 (is the judge trustworthy?)
>    must be read alongside §1a. A mode table you haven't validated the judge for is a
>    confident number nobody checked.

---

## 2. The assertion / judge split (requirement 2)

Four criteria were pulled OUT of the judge and implemented as deterministic
assertions (`eval/assertions.py`), and the judge prompt was reduced to a single
subjective criterion. Count: **4 assertions vs 1 judged criterion.**

| Moved to a free `if` + lookup (deleted from the judge prompt) | |
|---|---|
| A1 `section_resolves` | every `[Chunk … Section: S …]` citation resolves to a real section in that (policy, region) addendum |
| A2 `version_cited` | a handbook-version question cites the **current** effective date, not a mangled/absent/superseded one |
| A3 `notice_period_numeric` | a certification/notice answer contains an actual number |
| A4 `refusal_path` | out-of-jurisdiction/out-of-corpus → the exact refusal string |

| Left in the judge (needs reading the policy — a model earns its keep) | |
|---|---|
| `policy_correctness` | right entitlement/figure/band/outcome, or a correct refusal only when the corpus genuinely cannot answer. **Binary**, never 1–10. |

The judge_v1.txt prompt explicitly lists these four under **"DO NOT JUDGE"**, so they
are gone from the judge's job, not merely duplicated.

---

## 3. Before → after, and why the needle didn't move

`judge_v1.txt` → `judge_v2.txt` added two worked examples drawn from the judge's
**own** v1 disagreements (C17 and C22) plus a counter-example (C02-style), and a
sharpened refusal/boundary rule. Result:

```
AGREEMENT BEFORE -> AFTER :  86.2%  ->  86.2%   (delta +0.0 pts)
disagreements (v1): C02, C03, C17, C22
disagreements (v2): C02, C03, C17, C22   (identical — zero verdicts flipped)
```

The iteration changed the judge's *wording* (its v2 reasons now explicitly say "the
retrieved context genuinely lacks the figure") but **not one binary verdict**. A
single few-shot example did not override the judge's literal, context-grounded
reading. That is the honest result.

---

## 4. Disagreement analysis — who was right (requirement 4 + 5)

All four disagreements read in full. The retrieved context is decisive.

| Case | Human (blind) | Judge | Who was right | Why |
|---|---|---|---|---|
| **C02** | FAIL | PASS | **Judge** | The NA eligibility matrix (the 14-week figure) was **not retrieved** — only the "2. Primary Caregiver Leave" heading + the secondary-caregiver rule were. Refusing instead of inventing a number is correct **given the retrieved context**. My label judged against the whole corpus. |
| **C03** | FAIL | PASS | **Judge** | Same as C02: matrix not retrieved. A retrieval gap, not an answer error. |
| **C17** | FAIL | PASS | **Judge (defensibly)** | "How many sick days am I entitled to?" with no region; only UK sick-**pay** tiers retrieved (UK has no sick-day *count*). The context has no number to give. My FAIL was a product/UX stance ("ask the region"), not answer-vs-context correctness. |
| **C22** | FAIL | PASS | **Toss-up — I hold the human** | "3 years in" sits on the 36-month band boundary. The matrix WAS retrieved (14 wks @ 12–36, 18 wks @ >36). The judge takes 36 ∈ [12,36] → 14 wks (literal, defensible). I hold that confidently understating a paid-leave entitlement at a legal boundary, without flagging it, is wrong. |

**Verdict:** three of the four "disagreements" are **over-strict blind labels**, not
judge errors — the judge correctly grades against the *retrieved context*, while my
labels leaked knowledge of the full corpus. Only C22 is a genuine judgment call, and
even there the judge's reading is reasonable.

**Prediction scored (requirement 5): WRONG.** I predicted the few-shot would flip C17
and C22 to FAIL and lift agreement to ~93 %. It flipped neither and moved nothing.
The deeper mistake was framing C02/C03/C17 as judge faults at all; on the evidence the
judge was right and my labels were strict. (Full text: `prediction.txt`, OUTCOME.)

**The real bug the eval surfaced** is not the answer and not the judge — it is
**retrieval**: for C02/C03 the HR-208 NA eligibility matrix (`struct_HR-208_NA_3`) is
not retrieved, so the app honestly refuses. That is the Week-5 "false refusal" mode,
now correctly re-attributed to retrieval. Fixing retrieval (not the judge, not the
prompt) is the honest next step — and the judge is trustworthy enough (86 %, and
higher once the over-strict labels are acknowledged) to measure that fix.

---

## 5. Bonus — RAGAS faithfulness & context precision

Run: `python3.14 -m eval.ragas_bonus`. RAGAS faithfulness + context precision computed
with Gemini on the handbook-backed cases and on a constructed **superseded-version**
answer that cites HR-207 APAC §3.1 at the **2025-01-01** edition (15-day carry-over)
when the **current** 2026-01-01 edition says **10 days**.

| case | faithfulness | context precision | |
|---|---:|---:|---|
| C04, C05, C07, C11 | 1.00 | 1.00 | current |
| C06 | 0.89 | 0.83 | current |
| C09 | 0.86 | 1.00 | current |
| C10 | 0.83 | 1.00 | current |
| **BONUS_superseded** | **1.00** | **1.00** | **cites superseded 2025-01-01 (15 days)** |

```
avg faithfulness (current cases only) : 0.940
avg faithfulness (incl. superseded)   : 0.947   <- the stale answer RAISES the mean
```

The superseded answer scores **faithfulness 1.00** and **context precision 1.00** —
flawless, and literally indistinguishable from a correct answer — because faithfulness
asks *"is the answer supported by the retrieved text?"*, not *"is the retrieved text the
**current** handbook?"*. It is confidently, faithfully **wrong**. Averaged in with
genuinely-current cases it doesn't just hide — it *lifts* the mean from 0.940 to 0.947,
so no aggregate RAGAS dashboard would ever flag it. Only the deterministic
`A2_version_cited` assertion (A2) catches the stale citation, for free.
