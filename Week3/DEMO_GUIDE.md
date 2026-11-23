# Enterprise Global HR Leave Policy RAG Assistant: Live Demo Guide

This document provides the complete question-and-answer dataset, evaluation transcripts, architectural talking points, and verbatim speaker scripts for presenting both **Week 3** (RAG Fundamentals & Chunking) and **Week 4** (Debugging Retrieval, Hybrid Search & Failure Separation).

---

## Demo Overview: Week 3 vs. Week 4

| Demo Dimension | Week 3 Live Demo Track | Week 4 Live Demo Track |
| :--- | :--- | :--- |
| **Theme** | *Retrieval-Augmented Generation, From Parts* | *Debugging Retrieval — Hybrid, Reranking & Failure Separation* |
| **Core Story** | How naive sliding chunking breaks tables and creates cross-regional errors, and how structure-aware chunking + regional metadata filters solve it. | Why dense semantic search alone fails on exact alphanumeric codes (`HR-207 section 3.2`), and how failure triage (R vs G) and hybrid BM25+RRF buy back Hit@3. |
| **Key Artifacts** | `results.md` (8 Hit@5 questions, filter demo, 3 citations with `chunk_id`, 3 refusal transcripts). | Golden Set inspection view, R/G failure separation tally, Before vs After Hit@3 and p50 latency metrics. |
| **Live Command** | `python -m Services.bench_mark` | `python ask.py "What does HR-207 section 3.2 say about probationary carry-over?"` |

---

# Part 1: Week 3 Live Demo Guide

## 1.1 All 8 Benchmark Questions & Grounded Answers

Every answer below is strictly grounded in the 6 regional policy addenda and includes verified source citations formatted as `[Chunk: <chunk_id>, Policy: <id>, Section: <section>, Region: <region>]`.

---

### **Q1: Annual Leave Carry-Over for Tier 1 Probationary Staff (APAC)**
- **Question:** *"What is the annual leave carry-over cap for Tier 1 probationary staff in APAC?"*
- **Jurisdiction / Filter:** `region: APAC`
- **Expected Policy & Section:** Policy `HR-207`, Section `3.2`
- **Table Dependent:** Yes (Section 3.2 Probationary Employee Carry-Over Cap Table)
- **Resolved Chunk ID:** `struct_HR-207_APAC_4`
- **Generated Grounded Answer:**
  > "The annual leave carry-over cap for Tier 1 probationary staff in APAC is **3 days** [Chunk: struct_HR-207_APAC_4, Policy: HR-207, Section: 3.2, Region: APAC]. Employees under probation must obtain manager approval before utilizing carry-over leave during active probation periods [Chunk: struct_HR-207_APAC_4, Policy: HR-207, Section: 3.2, Region: APAC]."

---

### **Q2: Carry-Over Cap for Tier 2 Leads in Probation (APAC)**
- **Question:** *"What is the carry-over cap for Tier 2 Leads during probation in APAC?"*
- **Jurisdiction / Filter:** `region: APAC`
- **Expected Policy & Section:** Policy `HR-207`, Section `3.2`
- **Table Dependent:** Yes (Section 3.2 Table Row 2)
- **Resolved Chunk ID:** `struct_HR-207_APAC_4`
- **Generated Grounded Answer:**
  > "The carry-over cap for Tier 2 Leads during probation in APAC is **5 days**, with an expiration window of 90 days post-probation [Chunk: struct_HR-207_APAC_4, Policy: HR-207, Section: 3.2, Region: APAC]."

---

### **Q3: Probationary Leave Rollover Restriction (EMEA)**
- **Question:** *"Are unconfirmed probationary employees allowed to roll over leave in EMEA?"*
- **Jurisdiction / Filter:** `region: EMEA`
- **Expected Policy & Section:** Policy `HR-207`, Section `3.2`
- **Table Dependent:** Yes (Section 3.2 Probationary Restrictions Table)
- **Resolved Chunk ID:** `struct_HR-207_EMEA_4`
- **Generated Grounded Answer:**
  > "No, unconfirmed probationary employees in EMEA have a carry-over cap of **0 days** and are strictly prohibited from rolling over unused leave balances [Chunk: struct_HR-207_EMEA_4, Policy: HR-207, Section: 3.2, Region: EMEA]."

---

### **Q4: Parental Leave Duration for 24 Months of Service (North America)**
- **Question:** *"What is the paid leave duration for a primary caregiver with 24 months of service in North America?"*
- **Jurisdiction / Filter:** `region: NA`
- **Expected Policy & Section:** Policy `HR-208`, Section `2.1`
- **Table Dependent:** Yes (Section 2.1 Eligibility Matrix - Standard Tenure: 12-36 mos)
- **Resolved Chunk ID:** `struct_HR-208_NA_3`
- **Generated Grounded Answer:**
  > "A primary caregiver with 24 months of service in North America falls into the Standard tenure tier (12 to 36 months) and is eligible for **14 weeks of full pay**, with an optional 6-week unpaid extension allowed [Chunk: struct_HR-208_NA_3, Policy: HR-208, Section: 2.1, Region: NA]."

---

### **Q5: Category A Primary Caregiver Leave (LATAM)**
- **Question:** *"How many weeks of paid leave does a Category A primary caregiver receive in LATAM?"*
- **Jurisdiction / Filter:** `region: LATAM`
- **Expected Policy & Section:** Policy `HR-208`, Section `2.1`
- **Table Dependent:** Yes (Section 2.1 Primary Caregiver Scale)
- **Resolved Chunk ID:** `struct_HR-208_LATAM_3`
- **Generated Grounded Answer:**
  > "A Category A primary caregiver in LATAM receives **6 weeks of full paid leave**, backed by local statutory support [Chunk: struct_HR-208_LATAM_3, Policy: HR-208, Section: 2.1, Region: LATAM]."

---

### **Q6: Medical Absence Documentation Matrix (UK)**
- **Question:** *"What documentation is required for medical absences exceeding 8 days in the UK?"*
- **Jurisdiction / Filter:** `region: UK`
- **Expected Policy & Section:** Policy `HR-209`, Section `2.1`
- **Table Dependent:** Yes (Section 2.1 Notification Matrix - 8+ days row)
- **Resolved Chunk ID:** `struct_HR-209_UK_2`
- **Generated Grounded Answer:**
  > "For medical absences exceeding 8 days in the UK, employees must provide a **Statement of Fitness for Work (GP Fit Note)**, which entitles them to 100% pay for up to 4 weeks and 50% pay for the following 8 weeks [Chunk: struct_HR-209_UK_2, Policy: HR-209, Section: 2.1, Region: UK]."

---

### **Q7: Paid Paternity Leave for Non-Birthing Parents (LATAM)**
- **Question:** *"How many consecutive days of paid paternity leave do non-birthing parents receive in LATAM?"*
- **Jurisdiction / Filter:** `region: LATAM`
- **Expected Policy & Section:** Policy `HR-208`, Section `2.2`
- **Table Dependent:** No (Section 2.2 narrative text)
- **Resolved Chunk ID:** `struct_HR-208_LATAM_4`
- **Generated Grounded Answer:**
  > "Non-birthing parents in LATAM receive **15 consecutive calendar days of paid paternity leave** [Chunk: struct_HR-208_LATAM_4, Policy: HR-208, Section: 2.2, Region: LATAM]."

---

### **Q8: Carer's Conversion Cap for Year 2+ Employees (ANZ)**
- **Question:** *"What is the Carer's Conversion Cap for Year 2+ employees in ANZ?"*
- **Jurisdiction / Filter:** `region: ANZ`
- **Expected Policy & Section:** Policy `HR-209`, Section `2.1`
- **Table Dependent:** Yes (Section 2.1 Accumulation Schedule - Year 2+ row)
- **Resolved Chunk ID:** `struct_HR-209_ANZ_2`
- **Generated Grounded Answer:**
  > "For Year 2+ employees in ANZ, the Carer's Conversion Cap is a maximum of **8 days** from their 12 days of fully paid annual personal leave [Chunk: struct_HR-209_ANZ_2, Policy: HR-209, Section: 2.1, Region: ANZ]."

---

## 1.2 Out-of-Corpus Refusal Guardrail Tests

Strict refusal guardrail prevents hallucinations on questions not covered by the 6 leave addenda:

1. **Remote Work Stipends (APAC)**:
   - *Query*: *"What is the company policy on remote work stipends for APAC engineers?"*
   - *Response*: *"I do not have sufficient information in the provided leave policy documents to answer this question."* (0 citations generated)
2. **Paid Sabbaticals**:
   - *Query*: *"How many months of paid sabbatical leave are employees entitled to take after 5 years of service?"*
   - *Response*: *"I do not have sufficient information in the provided leave policy documents to answer this question."* (0 citations generated)
3. **Pet Bereavement Leave Cash-Out**:
   - *Query*: *"Can employees cash out unused pet bereavement leave under HR-208?"*
   - *Response*: *"I do not have sufficient information in the provided leave policy documents to answer this question."* (0 citations generated)

---

## 1.3 Week 3 Step-by-Step Live Presentation Script

### **1. Opening Hook & Context (30 seconds)**
> *"Good morning. Today I am presenting our **Enterprise Global HR Leave Policy RAG Assistant**.*
>
> *In global organizations, employees operate across multiple legal jurisdictions—APAC, EMEA, North America, LATAM, UK, and ANZ. Because each region enforces distinct statutory rules, probationary caps, and documentation requirements, standard LLMs create catastrophic legal hallucinations—such as quoting UK sick note rules to an employee in Sydney, or confusing EMEA zero-day probationary rollovers with APAC's 3-day cap.*
>
> *In Week 3, our mission was to build a grounded, regional RAG system from the ground up, prove which chunking strategy reliably indexes complex eligibility tables, and enforce deterministic refusals for ungrounded inquiries."*

### **2. The Chunking Battle: Strategy A vs Strategy B (60 seconds)**
> *"Our first engineering challenge was document chunking.*
>
> *We evaluated two distinct strategies over the 6 regional PDF addenda:*
> - *Strategy A: A fixed character sliding window (350 characters, 50-character overlap).*
> - *Strategy B: A structure-aware chunker that parses markdown `#` headers and numbered sections, anchoring the policy title to every child block and keeping tabular eligibility rows contiguous.*
>
> *When we ran our 8-question benchmark, Strategy B achieved a flawless **8/8 (100%)** Hit-in-Top-5.*
>
> *More importantly, we diagnosed a critical failure mode in Strategy A: On Question Q1—asking about probationary carry-over in APAC—Strategy A's sliding window sliced right through the middle of the table, severing the 'Tier 1 Staff' row from the document title. As a result, dense search retrieved an EMEA chunk at Rank 1. Strategy B solved this by attaching header anchors to every sub-chunk, ensuring the clause never loses its authoritative policy parent."*

### **3. Regional Metadata Isolation (45 seconds)**
> *(Execute or display Section 2 of `results.md`)*
>
> *"Next, observe what happens when an employee queries: 'What is the carry-over cap for probationary employees?' without regional filtering.*
>
> *Because both APAC and EMEA define probationary carry-over in Section 3.2, dense retrieval collides. The unfiltered query serves APAC at Rank 1 with a 0.8035 similarity score. If an EMEA employee in Frankfurt asked this question, they would erroneously be told they have 3 days of rollover, when EMEA policy strictly mandates zero days.*
>
> *By applying a strict Qdrant payload filter (`where region == 'EMEA'`), Rank 1 shifts directly to the EMEA policy document with a 0.7730 score, isolating 100% of the returned context to the employee's jurisdiction and eliminating cross-regional risk."*

### **4. Grounded Citations & Out-of-Corpus Refusals (45 seconds)**
> *(Show Section 3 and 4 of `results.md`)*
>
> *"Finally, notice our generation rigor. Every factual claim generated by `gemini-2.5-flash` resolves to an authoritative chunk ID, policy ID, and section: `[Chunk: struct_HR-207_APAC_4, Policy: HR-207, Section: 3.2, Region: APAC]`.*
>
> *And when asked ungrounded inquiries—such as remote work equipment stipends, 5-year sabbaticals, or cashing out pet bereavement leave—the model doesn't guess or extrapolate. It triggers our deterministic guardrail: 'I do not have sufficient information in the provided leave policy documents to answer this question.' Zero hallucinations. 100% auditability."*

---

# Part 2: Week 4 Live Demo Guide

## 2.1 The Problem: Dense Retrieval Blindspot on Exact Tokens

In Week 4, we evaluate what happens when real employees search using specific alphanumeric codes:
- Query: *"What does HR-207 section 3.2 say about probationary carry-over?"*
- Dense embedding models (like `gemini-embedding-001`) embed texts into a continuous semantic manifold. While excellent for semantic paraphrases (*"can I roll over holiday days"*), dense vectors compress token strings into dense geometric angles, making them structurally vulnerable to exact alphanumeric matching.
- Dense retrieval often fetches *"HR-208 section 2.1"* or *"HR-207 section 3.1"* because they share identical vocabulary about leave caps, but completely misses the exact section requested.

## 2.2 Failure Separation Taxonomy (R vs. G vs. Not-In-Corpus)

Before changing models or code, Week 4 requires inspecting every miss and classifying it into three mutually exclusive failure categories:

| Failure Label | Definition | Diagnostic Indicator | Solution Direction |
| :--- | :--- | :--- | :--- |
| **[R] Retrieval Failure** | The retriever failed to place the authoritative chunk into the Top-3 candidates. | Golden chunk is missing from Top-3 results; model never had the context. | Fix retrieval: Add BM25 keyword matching, tune chunk size, or add hybrid RRF. |
| **[G] Generation Failure** | The authoritative chunk was present in Top-3, but the LLM failed to synthesize or cited incorrectly. | Retrieved text clearly contains the answer, but generated output missed or hallucinated. | Fix prompt: Adjust system instruction, temperature, or citation formatting. |
| **[Not-In-Corpus]** | The query references a policy clause or concept not present in any indexed addendum. | No chunk contains the fact; model correctly refuses. | Expected behavior: Verified refusal transcript. |

## 2.3 The Single Retrieval Buy-Back: BM25 + RRF Hybrid Fusion

Instead of swapping the generation model (which costs latency and doesn't fix retrieval misses), Week 4 implements **exactly one retrieval change**:
- **BM25 Lexical Inverted Index**: Exact keyword matching over token terms (`HR-207`, `3.2`, `APAC`, `probationary`).
- **Reciprocal Rank Fusion (RRF, $k=60$)**: Combines ranks from Dense retrieval and BM25 lexical search:
  $$\text{Score}_{\text{RRF}}(d) = \frac{1}{60 + \text{Rank}_{\text{Dense}}(d)} + \frac{1}{60 + \text{Rank}_{\text{BM25}}(d)}$$
- **Result**: Dense retrieval captures semantic intent, while BM25 locks onto exact alphanumeric policy numbers, buying back Hit@3 on alphanumeric queries.

## 2.4 Week 4 Step-by-Step Live Presentation Script

### **1. Opening Problem Statement (30 seconds)**
> *"Welcome to the Week 4 Retrieval Debugging demonstration.*
>
> *In Week 3, our assistant answered semantic questions like 'how much parental leave do I get' with 100% accuracy. But in production, employees don't just ask natural language questions—they ask: 'What does HR-207 section 3.2 say about carry-over?'*
>
> *When we tested our baseline dense retriever against a 12-question golden set with exact alphanumeric tokens, dense retrieval struggled. The team lead's immediate reaction was: 'Let's swap the LLM to a bigger model.' But in engineering, before you change an LLM, you must inspect the failure modes and prove where the error actually lives."*

### **2. Failure Triage & Inspection View (45 seconds)**
> *"We opened our inspection view and audited all misses across our golden set, categorizing each into our Failure Taxonomy:*
> - *Is it an **[R]** failure, where retrieval failed to fetch the context?*
> - *Or a **[G]** failure, where retrieval succeeded but the LLM hallucinated?*
>
> *Our audit revealed that 100% of our misses were [R] failures—the dense retriever returned semantically adjacent paragraphs about annual leave, but none of them contained Section 3.2. Swapping the LLM would have accomplished nothing because the model never received the section."*

### **3. The Buy-Back: Hybrid BM25 + Reciprocal Rank Fusion (45 seconds)**
> *"To fix this, we made exactly ONE retrieval change: We introduced a BM25 lexical index fused with our dense embeddings via Reciprocal Rank Fusion with $k=60$.*
>
> *BM25 acts as an exact token anchor—locking onto 'HR-207' and '3.2'—while dense search preserves conceptual intent. When fused via RRF, the exact policy chunk leaped from outside the top 5 directly into Rank 1.*
>
> *This bought back our Hit@3 metric from baseline to target, while maintaining a lean p50 query latency. We fixed the exact alphanumeric R-failures without introducing generation overhead."*

---

# Part 3: Grader Defense & Q&A Cheatsheet

| Common Grader Question | Authoritative Defense & Talking Point |
| :--- | :--- |
| *"Why did you choose Structure-Aware chunking over a larger sliding window (e.g., 1000 chars)?"* | A 1000-char sliding window still places boundaries arbitrarily across character counts, meaning a table row can still be cleaved in two. Structure-Aware chunking parses AST-level markdown syntax (`#` headers, table row dividers), guaranteeing that eligibility tables remain contiguous units with their parent headings attached. |
| *"Why not just rely on metadata filtering for everything instead of hybrid search?"* | Metadata filters require structured extraction at ingestion time. If an employee queries a specific section clause inside a document (e.g., `section 3.2`), that section number is inside the chunk text, not a pre-defined DB column. BM25 keyword matching handles ad-hoc token matching across body text without requiring brittle schema migrations. |
| *"What is the precision vs. completeness tension demonstrated in your bonus challenge?"* | In our LATAM HR-208 Section 2.1 query on 'continuous service', tight structure-aware chunking achieved high retrieval precision (`0.7837`), but isolated the table from the preamble definitions. The model correctly refused because the definition was omitted. This proves that precision and completeness are in fundamental tension: tight chunks retrieve the exact number, but parent-child linking is required for definitions. |
