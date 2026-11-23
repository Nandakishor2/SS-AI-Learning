<!-- Soft Suave · The AI Engineering League -->
# Week 5 — Error Analysis Notes (HR Policy Assistant)

Domain: HR policy · Module M3 — Evals & Error Analysis · read ~20 real traces,
open-code, cluster, rank, predict. **Zero code changes were made while open-coding.**

---

## 0. How the traces exist (what was built this week)

The Week 4 app had **no trace logging** — there was nothing to read. So before any
analysis, the app was instrumented to emit one complete, replayable trace per query:

- `Services/trace_logger.py` — redaction + append-only `traces/traces.jsonl`.
- `Services/rag_engine.py` — now stamps every answer with a trace (`prompt_version`,
  `model`, `params`, `region_filter`, redacted `question`, retrieved `chunk_id`s **with
  scores and text**, and the redacted `raw_output`).
- `Services/generate_traces.py` — 30 varied, **unlabelled** production questions +
  10 curated demo questions, run live through the real app.
- `Services/sample_traces.py` — seeded random sample.
- `Services/replay.py` — rebuilds the prompt from a trace alone and re-generates.

Trace population: **30 production** + **10 demo** traces (`trc_0001`–`trc_0040`).

---

## 1. Replay evidence (one trace, replayed from the trace ALONE)

Seeded pick — `python -m Services.replay --seed 20260601` → **`trc_0008`**.
Replay rebuilds the prompt from the stored chunk texts + question (no re-retrieval),
re-calls the frozen model/params, and compares.

**Completeness check: all replay-critical fields present** — `prompt_version`
(`hr-rag-sys-v1`), `model` (`gemini-2.5-flash`), `params`
(`temperature=0.0, top_k=3, retriever=hybrid`), retrieved `chunk_id`s + scores + text,
`question`, `raw_output`. Nothing had to be added for this trace.

```
Q (trace):  ANZ, second year of service — how many personal leave days do I get and what's the carer's conversion cap?
retrieved:  [('struct_HR-209_ANZ_2', 0.032787), ('struct_HR-209_ANZ_1', 0.032002), ('struct_HR-209_ANZ_0', 0.032002)]

ORIGINAL raw_output:
  For employees in ANZ in their second year of service, you get 12 days of fully paid annual personal
  leave [Chunk: struct_HR-209_ANZ_2, Policy: HR-209, Section: 2.1, Region: ANZ]. The carer's conversion
  cap for this period is a maximum of 8 days [Chunk: struct_HR-209_ANZ_2, Policy: HR-209, Section: 2.1, Region: ANZ].

REPLAYED output (from trace alone):
  <byte-for-byte identical to ORIGINAL on this run>

MATCH: identical = True
```

**Reproducibility caveat (observed, not hypothetical):** re-running the replay later
produced a *semantically identical* answer (same 12 days, same 8-day carer cap, same cited
chunk `struct_HR-209_ANZ_2`) but with slightly different wording — `gemini-2.5-flash` is not
byte-deterministic even at `temperature=0`. Replay reliably reconstructs the **answer and
the cited chunk** from the trace alone; an exact byte match is a bonus, not a guarantee.

**Fields I could NOT fully reconstruct / caveats:**
- The trace records `model: gemini-2.5-flash`, which is a *moving server-side build*; an
  identical byte match is not guaranteed over time even at `temperature=0`. It matched today.
- For PII-bearing traces (e.g. `trc_0001`, `trc_0002`) the stored `question` is the
  **redacted** text, so a replay runs on the redacted question, not the raw one — faithful
  to what is on disk, but not to the exact string the employee typed.
- **Effective-date traces are degraded by redaction** (see Mode 5 / `trc_0023`): the date
  value is overwritten with `[PHONE_REDACTED]` before write, so the date cannot be
  recovered from the trace. This is a real gap in the record, left unfixed this week.

**Redaction confirmation:** employee names and IDs are redacted **before write**, inside
`build_trace()` (`redact()` runs on `question` and `raw_output` prior to `log_trace`). A
scan of `traces.jsonl` for the seeded PII (`Priya Menon`, `Daniel O'Brien`, `E-4471`,
`EMP-20233`) returns nothing. Redacted markers used: `[NAME_REDACTED]`, `[EMP_ID_REDACTED]`,
`[EMAIL_REDACTED]`, `[PHONE_REDACTED]`.

---

## 2. The seeded random sample (provable)

```
SEED        = 20260601
SOURCE POOL = production (30 traces)   # NOT the demo set, NOT remembered breakages
SAMPLE SIZE = 20
SELECTED    = trc_0001 trc_0002 trc_0003 trc_0004 trc_0005 trc_0006 trc_0008 trc_0011
              trc_0013 trc_0015 trc_0017 trc_0018 trc_0020 trc_0021 trc_0022 trc_0023
              trc_0027 trc_0028 trc_0029 trc_0030
```
Reproduce: `python -m Services.sample_traces` (defaults to this seed and n=20).

---

## 3. Open-coding — one honest OBSERVATION per trace (written before any grouping)

Descriptions of what happened. No categories, no diagnoses, no fixes.

1. **trc_0001** — Employee from the Singapore office asked about annual-leave carry-over; the APAC standard carry-over chunk WAS in the retrieved top-3, but the assistant replied "I do not have sufficient information."
2. **trc_0002** — London-based question about pay during a 10-day sick absence; the assistant answered "100% of your salary" and cited the UK notification-matrix chunk.
3. **trc_0003** — APAC carry-over question; the assistant said 10 days roll over and the excess is forfeited on March 31, citing the APAC carry-over chunk.
4. **trc_0004** — North America primary-caregiver question for ~2 years of service; the NA eligibility-matrix chunk was NOT in the top-3 and the assistant replied "I do not have sufficient information."
5. **trc_0005** — "What does section 3 of HR-207 cover?" with no region named; the top-3 mixed APAC, EMEA and NA chunks and the assistant replied "I do not have sufficient information."
6. **trc_0006** — Open "overview of the carry-over rules" question; the assistant returned the APAC (10-day, March 31) and EMEA (5-day, June 30) caps with citations.
7. **trc_0008** — ANZ second-year personal-leave question; the assistant answered 12 days and an 8-day carer's cap, citing the ANZ accumulation chunk.
8. **trc_0011** — Question about cashing out unused "pet bereavement leave" under HR-208; the assistant replied "I do not have sufficient information."
9. **trc_0013** — Question about what HR-210 says on jury-duty leave; the assistant replied "I do not have sufficient information."
10. **trc_0015** — "Difference between APAC and EMEA carry-over caps"; the assistant gave EMEA's 5-day cap but presented APAC only as the probation-tier table (3/5/10 days), and the APAC standard 10-day chunk was not in the top-3.
11. **trc_0017** — "How many sick days am I entitled to?" with no region named; the top-3 were all UK chunks and the assistant replied "I do not have sufficient information."
12. **trc_0018** — HR-208 §2.2 LATAM paternity question; the assistant answered 15 consecutive calendar days, citing the LATAM paternity chunk.
13. **trc_0020** — HR-207 §3.2 APAC Tier-1 probation question; the assistant answered a 3-day cap, citing the APAC probation table.
14. **trc_0021** — HR-209 UK 8+ day absence question; the assistant answered 100% pay for up to 4 weeks then 50% for the next 8 weeks, citing the UK matrix.
15. **trc_0022** — HR-208 NA secondary-caregiver question; the assistant answered 4 weeks fully paid after 90 days of service, citing the NA secondary-caregiver chunk.
16. **trc_0023** — "When did HR-209 take effect for ANZ?"; the assistant's answer gives the effective date as "[PHONE_REDACTED]", so no date is readable in the stored trace.
17. **trc_0027** — Sydney-office employee asking whether 2 sick days need a medical certificate; the assistant answered no (a certificate is required only beyond 2 consecutive days), citing the ANZ evidence chunk.
18. **trc_0028** — Berlin-based annual-leave question; the assistant answered 25 working days per year, citing the EMEA entitlements chunk.
19. **trc_0029** — LATAM primary caregiver with 8 months of service; the assistant answered 12 weeks of full paid leave, citing the LATAM caregiver scale.
20. **trc_0030** — Toronto primary caregiver with "3 years in"; the assistant answered 14 weeks plus a 6-week unpaid extension, reading 36 months as the 12–36-month band.

---

## 4. Clustering → named failure modes (done AFTER the sentences above)

See `taxonomy.md` for the ranked one-screen table. Members per mode:

- **M1 — Answerable question refused** (2/20, 10%): `trc_0001` (region+tenure given, right chunk even present), `trc_0004` (fully specified; matrix chunk not retrieved). Severity: annoys employee / avoidable tickets.
- **M2 — Refuses instead of asking which region** (2/20, 10%): `trc_0005`, `trc_0017` (no region given → ambiguous → flat refusal, no clarifying question). Severity: annoys.
- **M3 — Tenure boundary resolved to the lower band** (1/20, 5%): `trc_0030`. Severity: legal exposure (understates entitlement).
- **M4 — Comparison substitutes the wrong sub-rule for a region** (1/20, 5%): `trc_0015`. Severity: mild legal exposure.
- **M5 — Effective date erased from the trace by redaction** (1/20, 5%): `trc_0023`. Severity: compliance/audit exposure.

Non-failures observed: 11 correct answers (trc_0002, 0003, 0006, 0008, 0018, 0020, 0021,
0022, 0027, 0028, 0029) and 2 correct out-of-corpus refusals (trc_0011, trc_0013).

---

## 5. Dated, falsifiable prediction (committed before any fix)

Full text in `prediction.md`, committed at **git `cc32013`**
(`cc32013952ece067df09422e47bd4f2e22cb53ad`, 2026-11-04, before any code fix).

> Attack **M1**. One change: a pre-retrieval query-rewrite that maps city/office names to
> region codes and expands tenure phrases to policy units. Re-running the same 20 sampled
> questions, predict **M1 2/20 → 0/20** and the refusal family (M1+M2) **4/20 → ≤2/20**,
> by **2026-11-10**. False if M1 > 0/20 or the refusal family > 2/20 after the change.

---

## 6. Why a public benchmark would have missed the top-3 modes (3 sentences)

A high MMLU or HumanEval score certifies that the base model is broadly knowledgeable and
can write code, but it is scored on fixed public questions and never touches our private
HR addenda, our retriever, our prompt's refusal rule, or our logging — so it cannot reveal
that *this* app refuses answerable questions about *our* policies (M1/M2), understates an
NA paid-leave entitlement at a tenure boundary (M3), or that our own trace pipeline scrubs
effective dates out of the audit record (M5). Those modes live entirely in the interaction
between our corpus, our chunking, our hybrid retriever, our system prompt and our redaction
regex — none of which a leaderboard exercises. The benchmark would have told us the model
is "smart" and sent us shopping for a smarter one, which fixes none of the five modes above.

---

## 7. Bonus — random sample vs curated demo set

The 10 curated demo questions (`trc_0031`–`trc_0040`) are the clean, well-formed
policy+section+region questions always shown at the People-Ops review. Open-coded:

| trace | observation |
|---|---|
| trc_0031 | APAC Tier-1 §3.2 → answered 3 days, cited. (correct) |
| trc_0032 | LATAM §2.2 paternity → answered 15 days, cited. (correct) |
| trc_0033 | ANZ §2.1 year-2 → answered 12 days / 8-day carer cap. (correct) |
| trc_0034 | EMEA annual leave → answered 25 days; **effective date shows "[PHONE_REDACTED]"** (M5) |
| trc_0035 | UK 8+ days → GP Fit Note, 100% then 50%. (correct) |
| trc_0036 | NA primary caregiver, 2 yrs → **"I do not have sufficient information"** (M1); matrix chunk not retrieved |
| trc_0037 | NA secondary caregiver → 4 weeks / 90 days. (correct) |
| trc_0038 | ANZ effective date → **shows "[PHONE_REDACTED]"** (M5) |
| trc_0039 | APAC standard carry-over → 10 days. (correct) |
| trc_0040 | UK chronic-health → 5 discretionary days. (correct) |

**Top mode (M1) frequency — the two numbers:**

| | Random production sample | Curated demo set |
|---|---:|---:|
| M1 (answerable-but-refused) | **4/20 observed as refusals family; M1 = 2/20 = 10%** | **1/10 = 10%** |

(For a like-for-like single-number comparison of the exact top mode M1: random **2/20 = 10%**,
demo **1/10 = 10%**. The broader refusal family is **20% random vs 10% demo**.)

**What the team has been telling itself for the last month.** Every demo question is
pre-formatted the way the retriever likes it — explicit policy number, explicit section,
explicit region — so the review audience sees a near-perfect assistant and concludes "it
works, employees just need to phrase things clearly." Real traffic does the opposite: people
say "Singapore office" not "APAC," "2 years" not "24 months," and ask "how many sick days?"
with no region at all, which is exactly where the refusals cluster — so the refusal family
is **twice as frequent in the wild (20%) as in the demo (10%)**, and the whole M2 "no region
given" class is *structurally invisible* to a demo set where every question names its region.
The one refusal that still leaked into the demo (`trc_0036`, the NA caregiver matrix) was the
alarm bell the team explained away instead of sampling randomly to hear.

---

## 8. Reproduce everything

```bash
python -m Services.generate_traces     # (re)build the 40-trace population (live API)
python -m Services.sample_traces       # seed 20260601 → the 20 trace_ids above
python -m Services.replay --seed 20260601   # replay trc_0008 from the trace alone
```
