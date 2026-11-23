<!-- Soft Suave · The AI Engineering League -->
# Week 5 — Ranked Failure Taxonomy (HR Policy Assistant)

**Sample:** 20 production traces, seeded random (seed `20260601`) from a 30-trace
production pool. **Read by hand, no fixes applied.** Full open-coding in `notes.md`.
Prediction committed before any fix: git `cc32013`.

> Headline: the People-Ops lead reported *"it sometimes quotes the wrong policy."*
> Reading the traces, **wrong-policy quoting did not appear once**. The real top
> problem is the assistant **refusing questions it can actually answer** (4/20 = 20%
> across M1+M2). We would have fixed the wrong thing.

## Ranked modes

| Rank | Mode (what a stranger sees) | Count | Freq | Severity | Example |
|---|---|---:|---:|---|---|
| 1 | **Says "I don't have enough information" to a question the policies DO answer** — region & tenure were given (one case even had the right chunk retrieved) | 2/20 | 10% | Annoys employee; drives avoidable HR tickets; this is the lead's actual complaint | `trc_0001` |
| 2 | **Refuses instead of asking which region**, when the employee named no region | 2/20 | 10% | Annoys employee; forces a re-ask | `trc_0017` |
| 3 | **Tenure-boundary case resolved to the lower band** — "3 years" (36 mo) answered as the 12–36 band (14 wks), not >36 (18 wks) | 1/20 | 5% | Legal exposure — understates a paid-leave entitlement | `trc_0030` |
| 4 | **Multi-region comparison substitutes the wrong sub-rule** — APAC given as the probation table (3/5/10), not the plain 10-day standard cap | 1/20 | 5% | Mild legal exposure — misstates which cap applies | `trc_0015` |
| 5 | **Effective date erased from the trace record** — date logged as `[PHONE_REDACTED]` | 1/20 | 5% | Compliance/audit exposure — the record can't prove what date was quoted | `trc_0023` |

**Clean traces:** 11/20 correct answers + 2/20 correct refusals (out-of-corpus) = 13/20 behaved well.

## Fix target next week → Mode 1
One change: a pre-retrieval **query-rewrite** that maps city/office→region code and
expands tenure phrases to policy units. Predicted M1 **2/20 → 0/20**, refusal family
(M1+M2) **4/20 → ≤2/20**, by 2026-11-10. Full falsifiable prediction: `prediction.md` (git `cc32013`).
