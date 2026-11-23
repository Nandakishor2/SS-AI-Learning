"""
Week 6 — Build eval_set.jsonl from the real Week-5 traces.

Each case is one QUESTION (replayed verbatim from traces/traces.jsonl), tagged
with exactly one Week-5 taxonomy mode, plus the deterministic-assertion config and
a ground-truth note. Answers are NOT stored here — run_eval regenerates them LIVE
through the app, so the eval always scores the current app, and the regression
cases are true verbatim replays of real failed handbook traces.

Taxonomy modes (from taxonomy.md):
    M1_false_refusal        — answerable question, app wrongly refused        (fail mode)
    M2_region_disambiguation— no region given, app blind-refused              (fail mode)
    M3_tenure_boundary      — tenure band boundary resolved to the wrong band (fail mode)
    M4_multi_region         — multi-region compare crosses the wrong sub-rule (fail mode)
    M5_date_provenance      — effective-date / handbook-version provenance    (fail mode)
    clean_grounded          — "11/20 correct answers" clean category
    clean_refusal           — "2/20 correct out-of-corpus refusals" clean category

Run:  python3.14 -m eval.build_eval_set
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACES = ROOT / "traces" / "traces.jsonl"
OUT = ROOT / "eval" / "eval_set.jsonl"

# case_id, source trace_id, mode, regression?, applicable assertions, expected{}, note
CASE_SPEC = [
    # ---- M1 false refusal (answerable, app refused) ---------------------------
    ("C01", "trc_0001", "M1_false_refusal", True, ["A1_section_resolves"],
     {}, "Singapore=APAC; standard carry-over is 10 days. Answerable; refusing is wrong."),
    ("C02", "trc_0004", "M1_false_refusal", False, ["A1_section_resolves"],
     {}, "NA primary caregiver ~2yr -> 12-36mo band = 14 weeks. Answerable."),
    ("C03", "trc_0036", "M1_false_refusal", False, ["A1_section_resolves"],
     {}, "NA primary caregiver 2yr = 14 weeks. Answerable; refusing is wrong."),

    # ---- M2 region disambiguation (no region, app blind-refused) --------------
    ("C17", "trc_0017", "M2_region_disambiguation", True, [],
     {}, "No region given. Sick-leave rules differ UK/ANZ; blind refusal is a fail."),
    ("C18", "trc_0016", "M2_region_disambiguation", False, [],
     {}, "No region. Primary-caregiver scale differs NA/LATAM; should disambiguate."),
    ("C19", "trc_0005", "M2_region_disambiguation", False, [],
     {}, "Section 3 of HR-207 exists for APAC and EMEA with different caps; should disambiguate."),

    # ---- M3 tenure boundary ---------------------------------------------------
    ("C22", "trc_0030", "M3_tenure_boundary", True, ["A1_section_resolves"],
     {}, "Toronto=NA, '3 years in' = 36mo boundary. 12-36 band=14wk vs >36 band=18wk; the boundary must be flagged, not silently resolved down."),
    ("C29", "trc_0029", "M3_tenure_boundary", False, ["A1_section_resolves"],
     {}, "LATAM primary caregiver 8mo -> clearly Category B (6+mo) = 12 weeks. Tenure-scaled, unambiguous."),

    # ---- M4 multi-region comparison -------------------------------------------
    ("C20", "trc_0015", "M4_multi_region", True, ["A1_section_resolves"],
     {}, "Diff of standard carry-over caps: APAC 10 vs EMEA 5. Substituting APAC's probation table for its standard cap is the M4 fault."),
    ("C21", "trc_0006", "M4_multi_region", False, ["A1_section_resolves"],
     {}, "Overview of carry-over rules across regions; APAC 10 / EMEA 5 both correct."),

    # ---- M5 date provenance (handbook version) --------------------------------
    ("C27", "trc_0023", "M5_date_provenance", True, ["A2_version_cited"],
     {"effective_date": "2026-04-01", "policy": "HR-209", "region": "ANZ"},
     "When did HR-209 take effect for ANZ? Current handbook version = 2026-04-01."),
    ("C28", "trc_0024", "M5_date_provenance", False, ["A2_version_cited"],
     {"effective_date": "2026-02-01", "policy": "HR-207", "region": "EMEA"},
     "When does HR-207 become effective in EMEA? Current handbook version = 2026-02-01."),

    # ---- clean_grounded -------------------------------------------------------
    ("C04", "trc_0003", "clean_grounded", False, ["A1_section_resolves"],
     {}, "APAC carry-over: 10 days, forfeit Mar 31."),
    ("C05", "trc_0039", "clean_grounded", False, ["A1_section_resolves"],
     {}, "APAC standard carry-over cap = 10 days."),
    ("C06", "trc_0020", "clean_grounded", False, ["A1_section_resolves"],
     {}, "APAC Tier-1 probationary carry-over cap = 3 days (HR-207 3.2)."),
    ("C07", "trc_0018", "clean_grounded", False, ["A1_section_resolves"],
     {}, "LATAM non-birthing parent paternity = 15 days (HR-208 2.2)."),
    ("C08", "trc_0022", "clean_grounded", False, ["A1_section_resolves"],
     {}, "NA secondary caregiver = 4 weeks, needs 90 days service (HR-208 2.2)."),
    ("C09", "trc_0028", "clean_grounded", False, ["A1_section_resolves"],
     {}, "Berlin=EMEA annual leave = 25 working days (HR-207 2)."),
    ("C10", "trc_0040", "clean_grounded", False, ["A1_section_resolves"],
     {}, "UK chronic-health consultations = 5 discretionary days (HR-209 2.2)."),
    ("C11", "trc_0008", "clean_grounded", False, ["A1_section_resolves"],
     {}, "ANZ year 2 = 12 personal days, carer cap 8 (HR-209 2.1)."),
    ("C12", "trc_0007", "clean_grounded", False, ["A1_section_resolves", "A3_notice_period_numeric"],
     {"notice_numeric_required": True}, "UK sick 9 days -> GP Fit Note; 100% up to 4 wks then 50% next 8 wks."),
    ("C13", "trc_0002", "clean_grounded", False, ["A1_section_resolves", "A3_notice_period_numeric"],
     {"notice_numeric_required": True}, "London=UK sick 10 days -> 100% salary (within first 4 weeks)."),
    ("C14", "trc_0021", "clean_grounded", False, ["A1_section_resolves", "A3_notice_period_numeric"],
     {"notice_numeric_required": True}, "UK absence past 8 days -> 100% up to 4 wks then 50% next 8 wks."),
    ("C15", "trc_0027", "clean_grounded", False, ["A1_section_resolves", "A3_notice_period_numeric"],
     {"notice_numeric_required": True}, "Sydney=ANZ 2 days sick -> no certificate (cert needed only >2 consecutive days)."),
    ("C16", "trc_0019", "clean_grounded", False, ["A1_section_resolves"],
     {}, "ANZ yr2 under HR-209 2.1 -> 12 personal days, carer cap 8."),

    # ---- clean_refusal (out-of-corpus / out-of-jurisdiction) ------------------
    ("C23", "trc_0009", "clean_refusal", False, ["A4_refusal_path"],
     {"must_refuse": True}, "Sabbatical leave is not in any addendum -> must refuse."),
    ("C24", "trc_0010", "clean_refusal", False, ["A4_refusal_path"],
     {"must_refuse": True}, "Remote-work stipend is out of corpus -> must refuse."),
    ("C25", "trc_0013", "clean_refusal", False, ["A4_refusal_path"],
     {"must_refuse": True}, "HR-210 does not exist in the corpus -> must refuse."),
    ("C26", "trc_0014", "clean_refusal", False, ["A4_refusal_path"],
     {"must_refuse": True}, "HR-207 section 5 / sabbatical cap does not exist -> must refuse."),
]


def main():
    traces = {}
    with open(TRACES, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                t = json.loads(line)
                traces[t["trace_id"]] = t

    rows = []
    for case_id, tid, mode, regression, assertions, expected, note in CASE_SPEC:
        tr = traces[tid]
        rows.append({
            "case_id": case_id,
            "mode": mode,
            "regression": regression,
            "source_trace_id": tid,
            "question": tr["question"],
            "region_filter": tr.get("region_filter"),
            "assertions": assertions,
            "expected": expected,
            "ground_truth_note": note,
        })

    with open(OUT, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    modes = {}
    for r in rows:
        modes[r["mode"]] = modes.get(r["mode"], 0) + 1
    print(f"Wrote {len(rows)} cases -> {OUT.relative_to(ROOT)}")
    print(f"Regression cases (verbatim from failed traces): "
          f"{sum(1 for r in rows if r['regression'])}")
    for m, n in sorted(modes.items()):
        print(f"  {m:28s} {n}")


if __name__ == "__main__":
    main()
