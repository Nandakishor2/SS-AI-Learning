# Week 5: Error Analysis — Reading Traces Like a Professional

> **Scope Notice**: **This folder is Week 5** of the AI Engineering League (Module M3: Evals & Error Analysis). It is a direct extension of the Week 4 HR-policy RAG app (Hybrid BM25 + RRF retrieval), whose architecture is summarised in §6 below as the **foundation**. Week 4 asked *"is the right document retrieved?"*; **Week 5 asks *"what is actually going wrong in the answers, how often, and how badly — and which one do we fix first?"***

---

## 1. Problem Statement

The HR assistant has been running and the People-Ops lead reports it *"sometimes quotes the wrong policy."* That is not a bug report. This week we stop guessing: we make the app **record every answer as a replayable trace**, draw a **provably random sample of 20**, **read every one by hand**, write one honest observation per trace, cluster those into **named failure modes**, **rank them by frequency × severity**, and commit a **dated, falsifiable prediction** about the one mode we will fix next week — all with **zero code fixes applied during the analysis** (the zero is graded).

**Headline result:** reading the traces, *"quotes the wrong policy"* **never occurred**. The real #1 problem is the app **refusing questions it can actually answer** (20% of sampled traffic). Without error analysis we would have fixed the wrong thing.

---

## 2. What was added this week (the error-analysis pipeline)

Week 4 had **no trace logging** — answers were produced and discarded, so there was nothing to read. Week 5 adds the instrumentation and the analysis workflow:

| Component | File | Purpose |
| :--- | :--- | :--- |
| **Trace logger + redaction** | `Services/trace_logger.py` | Writes one complete, replayable trace per answer to `traces/traces.jsonl`. Redacts employee names / IDs / emails **before write**. |
| **Instrumented engine** | `Services/rag_engine.py` | `answer_query(..., log=True)` now stamps each answer with a trace (prompt version, model, params, retrieved `chunk_id`s **+ scores + text**, redacted question & output). |
| **Trace generator** | `Services/generate_traces.py` | Runs 30 varied *unlabelled* production questions + 10 curated demo questions through the live app and logs a trace for each. |
| **Seeded sampler** | `Services/sample_traces.py` | Draws a reproducible random sample of 20 production traces (seed pasted in `notes.md`). |
| **Replay tool** | `Services/replay.py` | Rebuilds the prompt from a stored trace **alone** and re-generates — proves the trace is complete. |
| **Terminal demo** | `run_week5.py` | Read-only walkthrough: population → redaction proof → seeded sample → inspection view → live replay → ranked taxonomy. |

### A trace is: **Question + what it Retrieved (chunk_ids + scores + text) + what it Answered**, plus bookkeeping (trace_id, timestamp, prompt_version, model, params). Complete enough to replay later without the live session.

---

## 3. Deliverables (what a reviewer reads)

| File | What it is |
| :--- | :--- |
| [`taxonomy.md`](./taxonomy.md) | **The one-page headline** — 5 failure modes ranked, each with count, frequency %, severity, and an example trace_id. |
| [`notes.md`](./notes.md) | **The full evidence** — 20 verbatim open-coding sentences, the seed + sampled trace_ids, the replay evidence, the redaction confirmation, the 3-sentence benchmark note, and the random-vs-demo bonus. |
| [`prediction.md`](./prediction.md) | **The dated, falsifiable prediction**, committed to git **before any fix** (commit `cc32013`). |
| `traces/traces.jsonl` | The 40 raw traces (30 production + 10 demo) the analysis is built on. |

> Note: [`results.md`](./results.md) is the **Week 4** deliverable (hit-rate@3 experiment), kept here as the foundation — it is **not** a Week 5 file.

---

## 4. The ranked failure taxonomy (summary)

Sample: 20 production traces, seeded random (seed `20260601`), read by hand.

| Rank | Mode (what a stranger sees) | Count | Freq | Severity | Example |
| :--- | :--- | :---: | :---: | :--- | :--- |
| 1 | "I don't have enough information" to a question the policies DO answer | 2/20 | 10% | Annoys / avoidable tickets (the lead's actual complaint) | `trc_0001` |
| 2 | Refuses instead of asking which region, when no region was given | 2/20 | 10% | Annoys / forces a re-ask | `trc_0017` |
| 3 | Tenure-boundary case resolved to the lower band (14 wks not 18) | 1/20 | 5% | **Legal** — understates a paid-leave entitlement | `trc_0030` |
| 4 | Multi-region comparison substitutes the wrong sub-rule for a region | 1/20 | 5% | Mild legal — misstates which cap applies | `trc_0015` |
| 5 | Effective date erased from the trace record (`[PHONE_REDACTED]`) | 1/20 | 5% | **Compliance/audit** — record can't prove the date quoted | `trc_0023` |

**Clean traces:** 11/20 correct answers + 2/20 correct out-of-corpus refusals = 13/20 behaved well. Full members + observations in `notes.md`.

---

## 5. Quick execution (Week 5)

> Use **`python3.14`** — it is the interpreter with the dependencies installed. Requires the Qdrant container running and a valid `.env` (`GEMINI_API_KEY`). See `INSTALLATION.md`.

```bash
# 0. (one-time) build the trace population by running 40 questions through the live app
python3.14 -m Services.generate_traces

# 1. the whole error-analysis demo, read-only (one live replay call)
python3.14 run_week5.py
python3.14 run_week5.py --no-replay      # fully offline, no API calls

# 2. individual steps
python3.14 -m Services.sample_traces              # seeded random 20 (seed 20260601)
python3.14 -m Services.replay --seed 20260601     # replay trc_0008 from the trace alone
python3.14 -m Services.replay trc_0023            # inspect the date-redaction finding

# 3. the original Week-4 chatbot still works (ask one question manually)
python3.14 ask.py "What is the carry-over cap for a Tier 1 probationary employee in APAC?"
```

---

## 6. Foundation — the Week 4 HR-RAG app this builds on

The underlying app (unchanged except for added trace logging): 6 regional leave-policy PDFs (HR-207/208/209 across APAC, EMEA, LATAM, NA, UK, ANZ) → structure-aware chunking → **28 chunks** in Qdrant → **Hybrid retrieval** (dense `gemini-embedding-001` 3072-dim + BM25, fused via Reciprocal Rank Fusion, k=60) → **Gemini 2.5 Flash** grounded generation with strict citations and refusal guardrails.

```text
6 Regional PDFs → Structure-Aware Chunks (28) → [ Dense Vector  +  BM25 Lexical ]
                                                        → RRF Fusion (k=60) → top-3
                                                        → Gemini 2.5 Flash (cited answer / refusal)
                                                        → *** Week 5: trace logged to traces.jsonl ***
```

Week 4's retrieval experiment (baseline Dense 9/12 → Hybrid 11/12 hit-rate@3, with the R/G/Not-In-Corpus tally and shipping decision) is documented in [`results.md`](./results.md), regenerated live by `python3.14 -m Services.bench_mark`.

---

## 7. Project Directory Tree

```text
Week5/
├── .env                       # API credentials (GEMINI_API_KEY) — git-ignored
├── .gitignore                 # excludes .env, __pycache__, qdrant_storage, .DS_Store
│
│   # ---- Week 5 deliverables ----
├── taxonomy.md                # ★ one-page ranked failure taxonomy (5 modes)
├── notes.md                   # ★ 20 open-coding sentences, seed+sample, replay, benchmark note, bonus
├── prediction.md              # ★ dated falsifiable prediction (committed before any fix)
├── traces/
│   └── traces.jsonl           # 40 recorded traces (30 production + 10 demo)
├── run_week5.py               # terminal demo / walkthrough
│
│   # ---- Week 4 foundation ----
├── results.md                 # Week 4 benchmark report (hit-rate@3, R/G tally, latency)
├── golden_set.jsonl           # Week 4: 12 real questions with known-correct chunk IDs
├── ask.py                     # interactive CLI chatbot (Hybrid retriever)
├── requirements.txt
├── INSTALLATION.md
├── data_drop/                 # 6 regional leave-policy PDFs
│   ├── HR-207_APAC.pdf  HR-207_EMEA.pdf
│   ├── HR-208_LATAM.pdf HR-208_NA.pdf
│   └── HR-209_ANZ.pdf   HR-209_UK.pdf
├── Services/
│   ├── __init__.py
│   ├── Chunker.py             # structure-aware header & table chunker
│   ├── injest.py              # PDF extraction & Qdrant ingestion
│   ├── hybrid_retriever.py    # Dense / BM25 / Hybrid (RRF k=60) retrievers
│   ├── rag_engine.py          # grounded engine  (+ Week 5 trace logging)
│   ├── bench_mark.py          # Week 4 benchmark runner → results.md
│   ├── ask.py                 # interactive question handler
│   ├── trace_logger.py        # ★ Week 5: trace schema + PII redaction
│   ├── generate_traces.py     # ★ Week 5: run question banks → traces.jsonl
│   ├── sample_traces.py       # ★ Week 5: seeded random sample of 20
│   └── replay.py              # ★ Week 5: replay a trace from the trace alone
├── Connection/gemini.py       # Gemini connectivity smoke test
└── qdrant_storage/            # local Qdrant vector DB (git-ignored)
```
