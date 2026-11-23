# Week 5 — Dated Prediction (committed BEFORE any fix)

**Date written:** 2026-11-04
**Author:** cutemoni041@gmail.com
**Target measurement date:** 2026-11-10 (Week 6)

## The ONE mode I will attack next week
**M1 — "I don't have enough information" on a question the corpus can actually answer.**
Observed in the seeded random sample (seed `20260601`, 20 production traces) at **2/20 = 10%**
(`trc_0001`, `trc_0004`). The wider refusal family (M1 + M2) is **4/20 = 20%**.

## The exact change (one change only)
Add a **pre-retrieval query-rewrite / normalization step** that runs before the existing
hybrid retriever and does two things:
1. Maps office/city names to region codes — Singapore→APAC, London→UK,
   Sydney/Auckland→ANZ, Berlin/Paris→EMEA, Toronto/New York→NA,
   Mexico City/São Paulo→LATAM — and appends the resolved region to the query.
2. Expands tenure phrases into the policy's own units — "2 years"→"24 months",
   "second year"→"12–36 months", etc.

Nothing else changes: same corpus, same chunker, same embedding model, same generator,
same prompt, same top-k=3.

## The falsifiable number
Re-running the **same 20 sampled questions** through the rewritten pipeline, I predict:

| Metric | Now | Predicted after change |
|---|---:|---:|
| M1 (answerable-but-refused) | 2/20 (10%) | **0/20 (0%)** |
| Refusal family (M1 + M2) | 4/20 (20%) | **≤ 2/20 (≤10%)** |

**This prediction is FALSE if**, after the change, M1 is still > 0/20, or the refusal
family is still > 2/20, measured on those same 20 trace questions by 2026-11-10.

## Why this is the right first target
M1 is the exact symptom the People-Ops lead is complaining about ("it doesn't help"),
it is the most clearly-wrong mode (the answer exists in the corpus and in one case was
already retrieved), and `trc_0001` shows a city-named region alone is enough to tip a
sufficient context into a refusal — the cheapest lever is to stop making the model guess
the region.
