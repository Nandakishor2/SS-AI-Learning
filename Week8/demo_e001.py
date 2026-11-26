#!/usr/bin/env python3
"""
Week 8 · E001 proof-on-one-screen (offline; reads the cached trajectory_eval results).

Thesis: getting E001's parental leave RIGHT (8 weeks) is not evidence the agent WORKS.
An answer-only eval passes the lucky guess. A trajectory eval — did it open the
employee's record before answering? — is what catches it.

    python3 demo_e001.py        # prints the proof; no API key needed
"""
import csv
from pathlib import Path

CSV = Path(__file__).resolve().parent / "trajectory" / "trajectory_eval.csv"
LABEL = {
    "v0_control":   "v0  hardened agent (reads record)",
    "v1_baseline":  "v1  + 'fast path' shortcut  <-- the bug",
    "v2_mitigated": "v2  + record-first guard (fix)",
}

rows = {r["variant"]: r for r in csv.DictReader(CSV.open()) if r["qid"] == "Q01"}

def yn(s):  # "True"/"False" -> tick/cross
    return "yes" if s == "True" else "NO"

print("\n" + "=" * 74)
print("  E001 (Aya Tanaka, NA, 6 mo tenure) — 'how many weeks fully paid leave?'")
print("  Ground truth: 8 weeks, HR-208   (her Early-Stage band happens to be 8)")
print("=" * 74)
print(f"  {'variant':<36}{'answer 8?':>10}{'record?':>10}{'verdict':>12}")
print("  " + "-" * 70)
for v in ("v0_control", "v1_baseline", "v2_mitigated"):
    r = rows[v]
    answer_ok = yn(r["outcome_pass"])          # did '8 weeks'+'HR-208' appear?
    opened    = yn(r["read_record"])           # did it call get_employee_record?
    verdict   = "TRUST" if r["trajectory_pass"] == "True" else "LUCKY GUESS"
    print(f"  {LABEL[v]:<36}{answer_ok:>10}{opened:>10}{verdict:>12}")
    print(f"      path: {r['name_seq']}")
print("  " + "-" * 70)

bug = rows["v1_baseline"]
print(f"""
  THE POINT (v1):
    - answer-only eval  : PASS  (it said '8 weeks, HR-208')
    - trajectory eval   : FAIL  (mode: {bug['mode']})
    - it took path '{bug['name_seq']}' and NEVER opened E001's record.
    - 8 is right ONLY because the shortcut's default equals Aya's band.
      Same shortcut on E002 -> should be 14, on E003 -> should be 18. It would
      still say the wrong thing confidently. E001 was never proof it works.

  Run the full picture (all 10 cases, the 20-pt outcome-vs-trajectory gap):
      python3 trajectory_eval.py --offline
""")
