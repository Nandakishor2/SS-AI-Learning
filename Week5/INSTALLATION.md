# Week 5: Installation & Execution Guide

> **Scope Notice**: **This folder is Week 5** of the AI Engineering League (*Error Analysis — Reading Traces Like a Professional*), a direct extension of the Week 4 HR-RAG app. The Week 5 error-analysis workflow is in **§6**; the Week 4 foundation (ingestion, retrieval benchmark) is in §§3–5. For the baseline Week 3 RAG setup, see [`../Week3/INSTALLATION.md`](file:///Users/softsuave/Desktop/AI-Learning-Production/Week3/INSTALLATION.md).

> **Interpreter note**: run everything with **`python3.14`** (the environment with the dependencies installed). Plain `python3` resolves to 3.12 here and lacks the packages.

---

## 1. Prerequisites

Ensure the following tools and services are available on your system:
- **Python**: Version 3.11+ (Python 3.14.x active in `./venv`)
- **Docker Desktop**: Running locally to host the Qdrant vector database container
- **Google Gemini API Key**: Valid key with access to `gemini-embedding-001` and `gemini-2.5-flash`

---

## 2. Environment Setup

### Step 2.1: Virtual Environment Activation

From the `Week4` project root:
```bash
# Activate existing virtual environment
# macOS / Linux:
source venv/bin/activate
# Windows:
# .\venv\Scripts\Activate.ps1
```

### Step 2.2: Dependencies Installation

Install the required packages from `requirements.txt`:
```bash
pip install -r requirements.txt
```

Key packages utilized in Week 4:
- `rank-bm25`: BM25 lexical keyword retrieval over tokenized policy text
- `google-genai`: Google Gemini SDK for 3072-dim embeddings & grounded generation
- `qdrant-client`: High-speed vector database client
- `pypdf`: PDF text extraction
- `python-dotenv`: Environment configuration

### Step 2.3: Configure Environment Variables

Confirm your `.env` file exists in the `Week4` root directory:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

Test your connection to Gemini:
```bash
python Connection/gemini.py
# Expected output: "Gemini response: Hello! Confirmed..."
```

---

## 3. Qdrant Vector Engine Startup

Ensure the Qdrant container is active and mapped to `./qdrant_storage`:

```bash
# Check if Qdrant container is already running
docker ps --filter "name=qdrant_rag"

# If stopped or not running, start it:
docker run -d -p 6333:6333 -p 6334:6334 \
  -v "$(pwd)/qdrant_storage:/qdrant/storage:z" \
  --name qdrant_rag \
  qdrant/qdrant
```

Verify the Qdrant Dashboard is accessible: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

---

## 4. Week 4 Pipeline Execution

### Step 4.1: Re-Ingest Policy Addenda (If vector store is clean)
```bash
# Parses the 6 regional PDF addenda into structure-aware chunks and loads them into Qdrant:
python -m Services.injest
```

### Step 4.2: Execute Week 4 Golden Set Benchmark & Report Generator
Runs the **12-question Golden Set** benchmark, compares **Baseline Dense Retrieval vs. Hybrid BM25+RRF ($k=60$)**, logs **Hit-rate@3 Before -> After**, measures **p50 Latency**, evaluates the **MMR Diversity Challenge**, and auto-generates `results.md`:

```bash
python -m Services.bench_mark
```

Output highlights printed to the terminal:
- Baseline Hit-rate@3 & p50 query latency.
- Inspection view failure tally: `[R]` (Retrieval failures), `[G]` (Generation failures), `[Not-In-Corpus]`.
- Hybrid BM25+RRF Hit-rate@3 & p50 query latency.
- Per-question resolution status: `[Preserved HIT]`, `[FIXED (R -> HIT)]`, `[Untouched (Not-In-Corpus)]`.
- Automatically generated/updated: [`results.md`](file:///Users/softsuave/Desktop/AI-Learning-Production/Week4/results.md).

### Step 4.3: Test End-to-End Generation & Guardrails
Evaluates grounded generation using the new Hybrid retriever, enforcing citations `[Chunk: <chunk_id>, Policy: <id>, Section: <sec>, Region: <reg>]` and honest refusals:

```bash
python -m Services.rag_engine
```

### Step 4.4: Interactive Querying with Source Inspection
Ask custom queries interactively or via CLI argument. Default retriever is Hybrid BM25+RRF:

```bash
python ask.py "What does HR-207 section 3.2 say about carry-over for probationary staff?"
```

Use `--retriever` (`-r`) to switch between the three methods for a side-by-side demo:

```bash
python ask.py "What does HR-207 section 3 cover for APAC?" -r cosine   # dense only  -> misses the section-3 chunk
python ask.py "What does HR-207 section 3 cover for APAC?" -r bm25     # lexical only -> finds it at rank 1
python ask.py "What does HR-207 section 3 cover for APAC?" -r hybrid   # fused (default) -> finds it in top-3
```

---

## 5. Week 4 Verification Checklist

- [x] `golden_set.jsonl`: 12 real employee questions with known-correct chunk IDs (7 with exact alphanumeric tokens).
- [x] Baseline Dense Hit-rate@3 measured and written down (`9/12`, 75.0%).
- [x] Baseline p50 latency measured (~540 ms/query; embedding-API dominated).
- [x] Failure separation completed with inspection-view evidence for every miss (tally: R=3, G=0, Not-In-Corpus=0).
- [x] Exactly ONE retrieval change applied: BM25 + Reciprocal Rank Fusion ($k=60$).
- [x] After Hybrid Hit-rate@3 measured (`11/12`, 91.7%) and After p50 latency measured (~540 ms/query).
- [x] Per-question fixed/unfixed/regression table: fixed `d01`/`d02`/`d03`, one regression `d09`.
- [x] [`results.md`](./results.md) is regenerated live by `python3.14 -m Services.bench_mark`.

---

## 6. Week 5 Pipeline Execution (Error Analysis)

Week 5 adds trace logging to the app and an error-analysis workflow on top. Qdrant must be running and `.env` present, exactly as above.

### Step 6.1: Generate the trace population (live API)
Runs 30 varied production questions + 10 curated demo questions through the live app and writes one complete trace per answer to `traces/traces.jsonl`. Employee names/IDs are redacted **before write**.
```bash
python3.14 -m Services.generate_traces          # fresh file (overwrites)
python3.14 -m Services.generate_traces --append # keep existing, add more
```

### Step 6.2: Draw the seeded random sample of 20
Reproducible — the seed is the only source of randomness, so anyone gets the same 20.
```bash
python3.14 -m Services.sample_traces            # seed 20260601, n=20, production pool
```

### Step 6.3: Replay a trace from the trace alone
Rebuilds the prompt from the stored chunks + question (no re-retrieval) and re-generates, proving the trace is a complete recording.
```bash
python3.14 -m Services.replay --seed 20260601   # seeded pick -> trc_0008
python3.14 -m Services.replay trc_0023          # the date-redaction finding
```

### Step 6.4: The full demo (read-only walkthrough)
```bash
python3.14 run_week5.py                 # population -> redaction proof -> sample -> inspection -> replay -> taxonomy
python3.14 run_week5.py --no-replay     # same, fully offline (no API calls)
```

---

## 7. Week 5 Verification Checklist

- [x] App instrumented to log a complete, replayable trace per answer (`Services/trace_logger.py`, `rag_engine.py`).
- [x] Employee names/IDs/emails redacted **before write**; `traces.jsonl` scanned clean of seeded PII.
- [x] Trace population generated: 30 production + 10 demo traces in `traces/traces.jsonl`.
- [x] Provable seeded random sample of 20 (seed `20260601`) — pasted in `notes.md`.
- [x] One honest OBSERVATION sentence per trace, written before grouping — **zero fixes applied during coding**.
- [x] 5 named failure modes with count, frequency %, severity, example trace_id (`taxonomy.md`).
- [x] One trace replayed from the trace alone, with completeness check + caveats (`notes.md`).
- [x] Dated, falsifiable prediction committed to git **before any fix** (commit `cc32013`, `prediction.md`).
- [x] 3-sentence note on why a public benchmark would miss the top modes (`notes.md`).
- [x] Bonus: curated demo set open-coded; top-mode frequency random vs demo reported (`notes.md`).
