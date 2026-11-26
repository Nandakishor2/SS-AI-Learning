<!-- Soft Suave · The AI Engineering League -->
# Week 6 — Validate the policy-answer judge before you trust its number

> **Scope:** Week 6 · Module M3 (Evals & Error Analysis). A direct extension of the
> Week-5 HR-policy RAG app. Week 5 asked *"what is going wrong in the answers?"*;
> **Week 6 asks *"the eval prints a correctness score from an LLM judge nobody ever
> checked — does that judge actually agree with a human, and can I move that
> agreement with evidence?"***

The headline number is **judge↔human agreement**, measured **before → after** one
honest iteration of the judge — with the human labels committed to git **before the
judge was ever run** (the ordering is the whole point).

---

## 1. Headline results

| Thing | Number |
|---|---|
| Eval cases (mode-tagged) | **29** (≥25), incl. **5 verbatim regression** replays |
| Deterministic assertions vs judged criteria | **4 assertions** vs **1 judged criterion** |
| Judge↔human agreement **before** (judge v1) | **86.2 % (25/29)** |
| Judge↔human agreement **after** (judge v2) | see `agreement_after.txt` |
| Blind protocol | labels committed in git commit **1**; judge first run in commit **2** |

Pass-rate-by-mode and the full agreement tables are reproduced by the two commands
below. The disagreement analysis and the honest scoring of the prediction are in
[`RESULTS.md`](./RESULTS.md).

---

## 2. The two commands

> Needs Qdrant running + `.env` with `GEMINI_API_KEY` (see `INSTALLATION.md`).
> Use `python3.14`. First run is live; add `--offline` afterwards to reuse the
> frozen answer snapshot and cached judge verdicts (no API / no Qdrant).

```bash
# (A) THE one-command eval — assertions + judge over 29 mode-tagged cases,
#     prints PASS RATE BY MODE (+ the assertion/judge split, + regression list)
python3.14 -m eval.run_eval                 # live, judge v1
python3.14 -m eval.run_eval --judge v2      # with the iterated judge
python3.14 -m eval.run_eval --offline       # reproducible, no API calls

# (B) Judge validation — agreement vs the BLIND labels, before -> after
python3.14 -m eval.validate_judge --both    # writes agreement_before/after.txt

# Bonus — RAGAS faithfulness + context precision, and the superseded-version demo
python3.14 -m eval.ragas_bonus
```

---

## 3. How each Week-6 requirement is met

| # | Requirement | Where |
|---|---|---|
| 1 | 25+ cases, each tagged one Week-5 taxonomy mode; ≥2 verbatim regression cases; one command prints pass rate by mode | `eval/eval_set.jsonl` (29 cases, 5 regression), `eval/run_eval.py` |
| 2 | Move ≥2 criteria out of the judge into deterministic assertions; delete them from the judge prompt; report assertion vs judged count | `eval/assertions.py` (**4**: section-resolves, version-cited, notice-numeric, refusal-path); judge prompt judges only `policy_correctness` (**1**). Count printed by `run_eval`. |
| 3 | Hand-label 25 answers blind on the single binary criterion, saved **before** the judge run, commit/timestamp proving order | `labels_25.json` (29 labels) committed in commit 1; judge first run in commit 2. `git log` is the proof. |
| 4 | Run judge, compute agreement %, iterate using 2 of its **own** disagreements as few-shot, re-measure; report before → after | `agreement_before.txt` (86.2 %) → `agreement_after.txt`; `judge_v1.txt` → `judge_v2.txt` adds C17 + C22 worked examples. |
| 5 | One-sentence prediction of what the iteration fixes, **before** iterating; report where it was wrong | `prediction.txt` (committed before `judge_v2.txt`); scored in `RESULTS.md`. |
| Bonus | RAGAS faithfulness + context precision; a 0.9+-faithfulness answer that cites a superseded version | `eval/ragas_bonus.py` |

### The single binary criterion
The judge grades exactly one thing — **`policy_correctness`**: *does the answer give
the substantively correct response per the governing policy (right figure/band/
outcome), or correctly refuse only when the corpus genuinely cannot answer?* Binary
PASS/FAIL — **not** a 1–10 score, because a judge cannot tell a 6 from a 7 and a
within-1 tolerance would inflate agreement into meaninglessness.

### What moved to `if` + a lookup table (and left the judge prompt)
1. **A1 section_resolves** — every `[Chunk … Section: S …]` citation resolves to a
   section that really exists in that (policy, region) addendum (`eval/corpus.py`).
2. **A2 version_cited** — a handbook-version question cites the **current** effective
   date, not a mangled/absent/superseded one.
3. **A3 notice_period_numeric** — a certification/notice answer contains a real number.
4. **A4 refusal_path** — an out-of-jurisdiction/out-of-corpus question triggers the
   exact refusal string.

These are free, reproducible, and never have an off day — so the judge never pays to
check them.

---

## 4. The eval set — modes (from `taxonomy.md`)

| Mode | Cases | What it probes |
|---|---|---|
| `M1_false_refusal` | 3 | answerable question the app refused |
| `M2_region_disambiguation` | 3 | no region given → blind refusal |
| `M3_tenure_boundary` | 2 | tenure band boundary resolved to the wrong band |
| `M4_multi_region` | 2 | multi-region comparison crosses the wrong sub-rule |
| `M5_date_provenance` | 2 | effective-date / handbook-version provenance |
| `clean_grounded` | 13 | straightforward answerable (correct baseline) |
| `clean_refusal` | 4 | correct out-of-corpus refusal |

**Regression cases** (verbatim replays of real failed Week-5 traces):
C01←trc_0001, C17←trc_0017, C20←trc_0015, C22←trc_0030, C27←trc_0023.

> Reporting one overall pass rate would hide that `M2_region_disambiguation` sits at
> the floor (33 % judge-scored / 0 % by the stricter human labels) while
> `clean_grounded` carries the average. `run_eval` prints per-mode; see `RESULTS.md`
> §1 for both views.

---

## 5. Files — complete structure

`★` = a Week-6 graded deliverable. Everything else is either the eval machinery that
produces those deliverables or the unchanged Week-5 app underneath.

```
Week6/
│
│  ── Week-6 deliverables (the graded artifacts) ───────────────────────────────
├── labels_25.json          ★ 29 BLIND human PASS/FAIL labels, committed in commit 1
│                              BEFORE the judge ever ran. Pins answers_sha256 + a UTC
│                              timestamp so the blind ordering is provable, not claimed.
├── judge_v1.txt            ★ Judge prompt v1 — grades ONE binary criterion
│                              (policy_correctness); the 4 deterministic criteria are
│                              listed under "DO NOT JUDGE" so they are gone, not duplicated.
├── judge_v2.txt            ★ Iterated judge — v1 + 2 worked examples drawn from the
│                              judge's OWN v1 disagreements (C17, C22) + a counter-example.
├── prediction.txt          ★ One-sentence prediction of what the iteration would fix,
│                              committed BEFORE judge_v2; OUTCOME appended after (scored WRONG).
├── agreement_before.txt    ★ Judge↔human agreement with v1 = 86.2% (25/29).
├── agreement_after.txt     ★ Judge↔human agreement with v2 = 86.2% (iteration moved nothing).
├── RESULTS.md              ★ The write-up: pass-rate-by-mode (both views), the assertion/
│                              judge split, before→after, full disagreement adjudication
│                              (who was right on C02/C03/C17/C22), prediction scored, bonus.
├── readme.md                 This file — scope, the two commands, requirement map.
├── INSTALLATION.md           Setup: Python 3.14 deps, Qdrant via Docker, .env / GEMINI_API_KEY.
├── requirements.txt          Python dependencies.
│
│  ── eval/ : the Week-6 harness (everything new is here) ─────────────────────
├── eval/
│   ├── eval_set.jsonl        29 mode-tagged cases (case_id, trace_id, mode, regression
│   │                           flag, question) — the frozen test set.
│   ├── build_eval_set.py     Regenerates eval_set.jsonl from traces/traces.jsonl; holds
│   │                           the CASE_SPEC (which trace each case replays, its mode, its
│   │                           applicable assertions, the expected outcome).
│   ├── eval_answers.jsonl     Frozen snapshot of the app's LIVE answers (+ retrieved
│   │                           chunks) that the labels and the judge are both scored against.
│   ├── corpus.py             The deterministic ground-truth lookup tables: which sections
│   │                           exist per (policy, region), each handbook's CURRENT effective
│   │                           date, and the exact refusal string. No model involved.
│   ├── assertions.py         The 4 deterministic assertions (section-resolves,
│   │                           version-cited, notice-numeric, refusal-path) — free `if` +
│   │                           lookup checks that replaced 4 judge criteria.
│   ├── judge.py              The LLM-as-judge: loads judge_v{1,2}.txt, calls Gemini at
│   │                           temp 0, parses the strict-JSON verdict, caches each verdict.
│   ├── common.py             Shared plumbing: load_cases(), and answers_for() which either
│   │                           regenerates answers live via the app or reuses the snapshot.
│   ├── run_eval.py          ★ THE one command — assertions + judge over all 29 cases,
│   │                           prints the per-case table and PASS RATE BY MODE + the split.
│   ├── validate_judge.py    ★ Compares judge verdicts to the blind labels, computes
│   │                           agreement before→after, writes agreement_*.txt + disagreements.json.
│   ├── ragas_bonus.py        Bonus — RAGAS faithfulness + context precision, incl. the
│   │                           "faithfully wrong" superseded-handbook demo.
│   ├── disagreements.json     Generated record of every judge↔human disagreement (the
│   │                           4 cases, with each side's reason) — the input to RESULTS.md §4.
│   └── .judge_cache.json      Cached judge verdicts (version:case_id:answer-hash) for
│                               reproducible, offline re-runs.
│
│  ── Week-5 foundation (the app being evaluated — unchanged) ─────────────────
├── taxonomy.md               Week-5 ranked failure taxonomy — defines the 5 modes every
│                               eval case is tagged with. The bridge from Week 5 to Week 6.
├── traces/traces.jsonl       Real Week-5 production traces — the source the regression
│                               cases (C01, C17, C20, C22, C27) are replayed verbatim from.
├── ask.py                    Root entry point to ask the assistant a question. Week 6
│                               also prints a live QUALITY CHECK panel per answer (same
│                               judge + assertions as the eval harness) — see Services/live_judge.py.
├── Connection/gemini.py      Gemini client / API-key wiring.
├── Services/
│   ├── injest.py             Ingest: PDFs → structure-aware chunks → embeddings → Qdrant.
│   ├── Chunker.py            Structure-aware (and baseline) chunking of the policy PDFs.
│   ├── hybrid_retriever.py   Hybrid retrieval: dense (gemini-embedding) + BM25, fused by RRF.
│   ├── rag_engine.py         The RAG core: retrieve → build grounded prompt → generate
│   │                           cited answer (answer_query is what the eval calls).
│   ├── ask.py                Interactive CLI loop over the RAG engine. Week 6: after each
│   │                           answer it runs the live judge panel (--no-judge to skip,
│   │                           --judge-version v1|v2 to pick the prompt).
│   ├── live_judge.py         ★ Week-6 add-on: wires the SAME eval judge + deterministic
│   │                           assertions into the interactive path, so an asker sees the
│   │                           PASS/FAIL verdict + the refusal / instruction-drift check live.
│   ├── usage_meter.py        ★ Week-6 add-on: meters the answer+judge calls (same prices
│   │                           as Week 7, for the before/after) and powers `--validate`,
│   │                           which proves a refusal is a retrieval gap (top_k=3 vs 10).
│   ├── trace_logger.py       Week-5 trace logging + PII redaction.
│   └── generate_traces.py    Week-5 script that produced the real trace population.
└── data_drop/                The 6 regional leave-policy PDFs (HR-207/208/209 ×
                                APAC/EMEA/LATAM/NA/ANZ/UK) — the knowledge base.
```

> Not in git (by `.gitignore`): `.env` (holds `GEMINI_API_KEY`), `qdrant_storage/`,
> `__pycache__/`. The `.env` is required to run but must never be committed.

---

## 6. Foundation (unchanged Week-5 app)

6 regional leave-policy PDFs → structure-aware chunks (28) in Qdrant → Hybrid
retrieval (dense `gemini-embedding-001` + BM25, RRF k=60) → Gemini 2.5 Flash grounded
generation with strict citations and a refusal guardrail. Week 6 adds the eval harness
on top; the RAG core (`rag_engine.py`, retrieval, chunking) is untouched. The one change
inside the app is `ask.py`, which now calls `Services/live_judge.py` to show the judge
verdict live — it reuses the eval graders, it does not re-implement them.


"I'm in Toronto and just had a baby as the primary caregiver with 3 years in — how many weeks paid and any unpaid extension?"