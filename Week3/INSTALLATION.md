# Installation & Environment Setup Guide: Week 3 & Week 4

This guide covers setting up the local runtime environment, launching the Qdrant vector database container, indexing regional policy addenda, and executing the retrieval, evaluation, and generation pipelines for **Week 3** (RAG Fundamentals & Chunking) and **Week 4** (Debugging Retrieval, Hybrid Search & Failure Separation).

---

## 1. Prerequisites

Before starting, ensure the following tools are installed and operational:
- **Python**: Version 3.11, 3.12, 3.13, or 3.14.
- **Docker Desktop**: Running locally (required for hosting the Qdrant vector store).
- **Google Gemini API Key**: Valid API key with access to:
  - `gemini-embedding-001` (Dense 3072-dimensional embeddings)
  - `gemini-2.5-flash` (Deterministic grounded generation)

---

## 2. Environment Setup

### Step 2.1: Clone / Navigate to Workspace & Create Virtual Environment

```bash
# Navigate to the project root
cd Week4

# Create a local virtual environment
python3 -m venv venv

# Activate the virtual environment
# macOS / Linux:
source venv/bin/activate
# Windows PowerShell:
# .\venv\Scripts\Activate.ps1
```

### Step 2.2: Install Dependencies

Install all core dependencies specified in `requirements.txt`:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Key packages installed:
- `google-genai`: Official Google Gemini GenAI SDK
- `qdrant-client`: High-performance vector database client
- `pypdf`: Robust extraction of text from policy PDFs
- `python-dotenv`: Environment variable loading

### Step 2.3: Configure API Credentials

Ensure a `.env` file exists in the root directory:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

Verify the API connection:
```bash
python Connection/gemini.py
# Expected output: "Gemini response: Hello! Confirmed..."
```

---

## 3. Vector Database Setup (Docker Qdrant)

Launch the official Qdrant Docker container with persistent local disk storage mapped to `./qdrant_storage`:

```bash
# Launch Qdrant container
docker run -d -p 6333:6333 -p 6334:6334 \
  -v "$(pwd)/qdrant_storage:/qdrant/storage:z" \
  --name qdrant_rag \
  qdrant/qdrant
```

*Note: If `qdrant_rag` is already running from Week 3, confirm it is healthy:*
```bash
docker ps --filter "name=qdrant_rag"
```
Verify the Qdrant Web UI Dashboard is accessible at: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

---

## 4. Pipeline Execution: Week 3 vs. Week 4

### 4.1 Week 3 Execution Pipeline: Core RAG & Chunking Benchmark

Week 3 focuses on evaluating **Strategy A (Baseline Sliding Window)** vs. **Strategy B (Structure-Aware Header & Table chunker)**, verifying **Hit-in-Top-5**, demonstrating **Regional Metadata Filtering**, and enforcing **Grounded Citations + Out-of-Corpus Refusals**.

```bash
# Step 1: Ingest 6 PDF regional addenda into Qdrant
# Parses PDFs, attaches 4 mandatory metadata fields + chunk_id, and creates 3072-dim embeddings
python -m Services.injest

# Step 2: Run the 8-Question Benchmark & Metadata Filtering Demo
# Evaluates Hit@5 for both chunking strategies, runs EMEA filter demo, and auto-generates results.md
python -m Services.bench_mark

# Step 3: Run Grounded Generation & Refusal Test Suite
# Tests 3 answerable table questions with [Chunk: <id>, Policy: <id>, Section: <sec>, Region: <reg>]
# Tests 3 out-of-corpus queries with deterministic refusal transcripts
python -m Services.rag_engine

# Step 4: Run Ad-Hoc Interactive Querying (Optional)
python ask.py "What is the annual leave carry-over cap for Tier 1 probationary staff in APAC?"
```

**Week 3 Deliverable Check**:
Review [`results.md`](file:///Users/softsuave/Desktop/AI-Learning-Production/Week4/results.md) for:
- 8-question benchmark table with known-correct policy IDs and sections.
- Both Hit@5 numbers (`8/8` for Strategy A, `8/8` for Strategy B).
- Complete search-only dumps for both chunking strategies.
- Unfiltered vs Filtered retrieval lists with similarity scores.
- 3 cited answers with resolvable `chunk_id`s and 3 refusal transcripts.
- Chunking strategy defense and diagnosed failure on APAC table fragmentation.
- Bonus challenge: Precision vs completeness tension on continuous service query.

---

### 4.2 Week 4 Execution Pipeline: Retrieval Debugging & Hybrid Search

Week 4 builds directly upon the Week 3 foundation by debugging dense retrieval failures on exact alphanumeric tokens (e.g. `"HR-207 section 3.2"`), classifying misses via **Failure Taxonomy (R / G / Not-In-Corpus)**, and measuring retrieval buy-back via **Hybrid Search (Dense + BM25 with RRF)**.

```bash
# Step 1: Inspect retrieval on exact token queries
# Notice how dense search alone struggles when querying exact policy numbers:
python ask.py "What does HR-207 section 3.2 say about probationary employee carry-over?"

# Step 2: Run Golden Set (12 Questions) Baseline Hit@3 Measurement
# Evaluates baseline dense retriever against the 12-question golden set with exact tokens:
python -m Services.bench_mark

# Step 3: Failure Separation Inspection
# Inspect retrieved chunks in results.md to triage misses into:
# - [R]: Retrieval missed correct chunk in Top-3
# - [G]: Top-3 had correct chunk, but generator failed or mis-cited
# - [Not-In-Corpus]: Valid gap requiring refusal

# Step 4: Run Single Retrieval Change Buy-Back
# Evaluates BM25 lexical keyword matching fused with dense vectors via Reciprocal Rank Fusion (RRF, k=60)
# Measures Hit@3 Before -> After and p50 query latency
```

---

## 5. Verification & Troubleshooting Checklist

| Issue | Root Cause | Solution |
| :--- | :--- | :--- |
| `Failed to connect to Qdrant at localhost:6333` | Docker container is stopped or not mapped to port 6333. | Run `docker start qdrant_rag` or re-execute the `docker run` command in Step 3. |
| `API_KEY_INVALID` or `403 Forbidden` | `GEMINI_API_KEY` missing or expired in `.env`. | Verify valid key in `.env` and run `python Connection/gemini.py` to confirm. |
| `No PDF files found in ./data_drop` | Working directory is inside `Services/` instead of project root. | Always run commands from the project root using `python -m Services.<module>`. |
| Cross-regional collision in query results | Region filter was omitted in multi-jurisdiction query. | Specify `region` parameter (e.g., `answer_query(q, region="EMEA")`). |
