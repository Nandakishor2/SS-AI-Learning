# Enterprise Global HR Leave Policy RAG Assistant

A production-grade Retrieval-Augmented Generation (RAG) system and retrieval debugging framework designed to parse, index, search, and answer employee leave policy queries across six regional jurisdictions (APAC, EMEA, NA, LATAM, UK, ANZ) with strict grounding, source citations, regional metadata isolation, and deterministic out-of-domain refusals.

This repository tracks the technical evolution across **Module 2 (Retrieval & RAG)**:
- **Week 3**: *Retrieval-Augmented Generation, From Parts* (Dual Chunking Strategies, Metadata Payloads, Hit@5 Benchmarking, Grounded Citations & Refusals).
- **Week 4**: *Debugging Retrieval — Hybrid, Reranking & Failure Separation* (12-Question Golden Set, Failure Taxonomy R/G/Not-In-Corpus, BM25 + RRF Hybrid Fusion, Hit@3 & p50 Latency Optimization).

---

## Technical Differentiation: Week 3 vs. Week 4

The following matrix outlines the conceptual and architectural distinction between Week 3 and Week 4:

| Capability / Dimension | Week 3: Core RAG & Structural Chunking | Week 4: Debugging Retrieval & Hybrid Reranking |
| :--- | :--- | :--- |
| **Primary Focus** | Building end-to-end RAG baseline from PDF addenda with structure-aware chunking. | Diagnosing retrieval misses, separating failure modes, and buying back Hit@3 with hybrid search. |
| **Document Ingestion** | 6 regional PDF addenda parsed into Markdown/plain text blocks. | Ingested chunks mapped to explicit token-searchable indices (Dense + Inverted BM25 index). |
| **Chunking Strategies** | **Strategy A**: Naive sliding-window (350 chars, 50-char overlap).<br>**Strategy B**: Structure-aware parser preserving headers (`#`, `##`, `###`) and tables. | Structure-aware chunking maintained with granular chunk IDs and inverted index tokens for exact token matches. |
| **Embedding & Storage** | Google `gemini-embedding-001` (3072-dim, Cosine) stored in Qdrant collections (`baseline_chunks`, `structure_chunks`). | Dense vectors + Sparse BM25 token frequencies; stored in Qdrant with Reciprocal Rank Fusion (RRF, $k=60$). |
| **Retrieval Strategy** | Dense semantic vector search + Qdrant metadata payload filter (`where region == 'EMEA'`). | **Hybrid Search**: Dense Vector Retrieval + BM25 Lexical Keyword Retrieval combined via RRF. |
| **Evaluation Benchmark** | **8-Question Known-Answer Benchmark** (6 table-dependent) evaluating **Hit-in-Top-5**. | **12-Question Golden Set** (at least 4 exact token queries: policy IDs, sections, dates) evaluating **Hit-rate@3**. |
| **Failure Analysis** | Documenting table fragmentation and embarrassing chunk boundary failures in Strategy A. | **Formal Failure Taxonomy**: Triage every miss into **R** (Retrieval miss), **G** (Generation misuse), or **Not-In-Corpus**. |
| **Generation & Safety** | Strict prompt grounding with exact citation: `[Chunk: <id>, Policy: <id>, Section: <sec>, Region: <reg>]` + honest refusals. | Grounded generation evaluated before and after retrieval buy-back; tracking p50 latency impact. |
| **Key Deliverables** | `results.md` (Hit@5 table, filter demo, 3 cited answers, 3 refusals, chunker defense, bonus tension analysis). | `week4_results.md` (Golden set, Hit@3 before/after, p50 latency before/after, R/G tally, fixed vs untouched R-failures). |

---

## System Architecture

```text
                                  +---------------------------------------+
                                  |     6 Regional Leave Policy PDFs      |
                                  |     (APAC, EMEA, LATAM, NA, UK, ANZ)  |
                                  +-------------------+-------------------+
                                                      |
                             +------------------------+------------------------+
                             |                                                 |
                             v                                                 v
              +-------------------------------+               +-------------------------------+
              |     Week 3: Chunking Lab      |               |     Week 4: Hybrid Lab        |
              | Strategy A: 350-char sliding  |               | BM25 Lexical Inverted Index   |
              | Strategy B: Structure-aware   |               | + Dense Vector Cosine Embed   |
              +---------------+---------------+               +---------------+---------------+
                              |                                               |
                              v                                               v
              +-------------------------------+               +-------------------------------+
              | Qdrant Vector Store (:6333)   |               | Reciprocal Rank Fusion (RRF)  |
              | - baseline_chunks (17 chunks) |               | score = 1 / (60 + rank_dense) |
              | - structure_chunks (28 chunks)|               |       + 1 / (60 + rank_bm25)  |
              +---------------+---------------+               +---------------+---------------+
                              |                                               |
                              +-----------------------+-----------------------+
                                                      |
                                                      v
                                      +-------------------------------+
                                      |      Query & Inspection       |
                                      | - Regional Filter (Metadata)  |
                                      | - Failure Triage (R vs G)     |
                                      +---------------+---------------+
                                                      |
                                                      v
                                      +-------------------------------+
                                      | Gemini 2.5 Flash Generation   |
                                      | - Temp: 0.0 (Deterministic)   |
                                      | - Resolvable Chunk Citations  |
                                      | - Refusal Guardrail Trigger   |
                                      +-------------------------------+
```

---

## Project Directory Tree

```text
Week4/
├── .env                       # API credentials (GEMINI_API_KEY)
├── INSTALLATION.md            # Environment setup & dual-week execution guide
├── readme.md                  # System overview, architecture & Week 3 vs Week 4 matrix
├── DEMO_GUIDE.md              # Live demo script, Q&A datasets & speaker talking points
├── results.md                 # Week 3 benchmark report (Hit@5, Filter demo, Citations, Refusals)
├── ask.py                     # Root CLI for interactive queries across all regional policies
├── data_drop/                 # 6 Regional leave policy PDF documents
│   ├── HR-207_APAC.pdf        # Annual leave, probationary caps, accruals
│   ├── HR-207_EMEA.pdf        # Annual leave, rollover restrictions
│   ├── HR-208_LATAM.pdf       # Primary caregiver scale, paternity leave
│   ├── HR-208_NA.pdf          # Tenure-tiered caregiver matrix, secondary leave
│   ├── HR-209_ANZ.pdf         # Personal/carer leave, accumulation schedules
│   └── HR-209_UK.pdf          # Medical notification matrix, GP fit note rules
├── Services/
│   ├── __init__.py
│   ├── Chunker.py             # Strategy A (Sliding Window) vs Strategy B (Structure-Aware)
│   ├── injest.py              # PDF extraction, embedding & Qdrant upsert with metadata
│   ├── bench_mark.py          # Week 3: 8-question Hit@5 benchmark, filtering demo & results.md generator
│   ├── rag_engine.py          # Week 3: Grounded synthesis, chunk_id citation & refusal engine
│   └── ask.py                 # Interactive question handler with source inspection
└── qdrant_storage/            # Persistent local Qdrant vector database storage
```

---

## Technical Highlights

### Week 3 Capabilities
- **Dual Chunking Strategies**:
  - **Baseline Chunker**: Fixed 350-character window with 50-character overlap (17 chunks).
  - **Structure-Aware Chunker**: Markdown header (`#`, `##`, `###`) and numbered section parser preserving parent hierarchy and tabular rows intact (28 chunks).
- **Mandatory Metadata Ingestion**:
  - Every chunk in Qdrant contains: `source_file`, `policy_id`, `region`, `effective_date`, and `chunk_id`.
- **Retrieval Benchmark (Hit-in-Top-5)**:
  - 8 ground-truth operational questions covering all 6 jurisdictions (6 table-dependent).
  - Baseline Chunker: **8/8 (100%)**
  - Structure-Aware Chunker: **8/8 (100%)**
- **Metadata Filtering**:
  - Evaluated on `"What is the carry-over cap for probationary employees?"`.
  - Unfiltered query returns APAC at Rank 1 (Score: `0.8035`).
  - Filtered query (`region == 'EMEA'`) shifts Rank 1 directly to EMEA (Score: `0.7730`), isolating jurisdiction and preventing cross-regional hallucinations.
- **Strict Grounding & Refusals**:
  - Resolvable citations: `[Chunk: <chunk_id>, Policy: <policy_id>, Section: <section>, Region: <region>]`.
  - 100% honesty on out-of-corpus inquiries: `"I do not have sufficient information in the provided leave policy documents to answer this question."`.

### Week 4 Capabilities
- **Exact Token Failure Diagnosis**:
  - Dense semantic retrieval struggles on exact alphanumeric tokens (e.g. searching for `"HR-207 section 3.2"` often retrieves semantically adjacent clauses from other sections or documents).
- **12-Question Golden Set**:
  - 12 real employee queries with known-correct chunk IDs, including at least 4 exact token queries (policy codes, section numbers, effective dates).
- **Inspection View & Failure Separation (R vs G vs Not-In-Corpus)**:
  - **R (Retrieval miss)**: Retriever failed to place correct chunk into Top-3.
  - **G (Generation failure)**: Correct chunk retrieved in Top-3, but LLM failed to synthesize or cite correctly.
  - **Not-In-Corpus**: Legitimate gap in policy addenda; verified refusal required.
- **Single Retrieval Buy-Back (BM25 + RRF Hybrid Search)**:
  - Adds BM25 keyword matching fused with dense embeddings via Reciprocal Rank Fusion ($k=60$).
  - Measures **Hit@3 Before vs After** and evaluates **p50 query latency** overhead.

---

## Quick Execution

### Running Week 3 Pipelines
```bash
# 1. Ingest PDF policies into Qdrant vector store
python -m Services.injest

# 2. Run Week 3 Hit-in-Top-5 benchmark & generate results.md
python -m Services.bench_mark

# 3. Run Grounded Generation & Refusal test suite
python -m Services.rag_engine

# 4. Interactive questioning across all regional policies
python ask.py "What is the annual leave carry-over cap for Tier 1 probationary staff in APAC?"
```

### Running Week 4 Pipelines
```bash
# 1. Inspect retrieval failures on exact tokens
python ask.py "What does HR-207 section 3.2 say about probationary carry-over?"

# 2. Review failure separation and hybrid benchmark deliverables in results.md
cat results.md
```