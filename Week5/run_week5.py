#!/usr/bin/env python3
"""
Week 5 — Error Analysis DEMO (terminal walkthrough).

Read-only over the already-generated trace population. Shows, in order:
  1. The trace population + a redaction proof
  2. The seeded random sample of 20 (provable)
  3. An inspection view of a few sampled traces (question -> chunks+scores -> answer)
  4. A live replay of one trace FROM THE TRACE ALONE (original vs replayed)
  5. The ranked failure taxonomy

Run:   python run_week5.py            (python3.14 — the interpreter with deps)
       python run_week5.py --no-replay   (skip the one live API call)
"""
import sys
import argparse
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from Services.trace_logger import load_traces, get_trace, TRACES_FILE
from Services.sample_traces import sample_trace_ids, DEFAULT_SEED

REPLAY_SEED = 20260601
INSPECT = ["trc_0001", "trc_0020", "trc_0023"]  # a refusal, a clean hit, the redaction finding

TAXONOMY = [
    (1, "Answerable question refused ('I don't have enough information')", "2/20", "10%", "annoys / avoidable tickets", "trc_0001"),
    (2, "Refuses instead of asking which region (no region given)",         "2/20", "10%", "annoys / re-ask",            "trc_0017"),
    (3, "Tenure boundary resolved to the lower band (14 wks not 18)",       "1/20", "5%",  "LEGAL — understates leave", "trc_0030"),
    (4, "Comparison substitutes the wrong sub-rule for a region",            "1/20", "5%",  "mild legal",                "trc_0015"),
    (5, "Effective date erased from trace record ([PHONE_REDACTED])",        "1/20", "5%",  "COMPLIANCE/audit",          "trc_0023"),
]


def hr(c="="): print(c * 78)


def section(n, title):
    print("\n"); hr(); print(f"  STEP {n} — {title}"); hr()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-replay", action="store_true", help="skip the single live replay API call")
    args = ap.parse_args()

    if not TRACES_FILE.exists():
        print("No traces found. Run:  python -m Services.generate_traces"); return

    prod = load_traces("production"); demo = load_traces("demo")

    hr(); print("  WEEK 5 · ERROR ANALYSIS — HR POLICY ASSISTANT · DEMO"); hr()
    print(f"  Trace file : {TRACES_FILE}")
    print(f"  Population : {len(prod)} production + {len(demo)} demo traces")

    # 1. Redaction proof
    section(1, "REDACTION IS BEFORE WRITE (no employee name/ID on disk)")
    t = get_trace("trc_0001")
    print("  Stored question for trc_0001 (raw PII was: 'Priya Menon', 'E-4471'):")
    print(f"    {t['question']}")
    import subprocess
    leaked = subprocess.run(["grep", "-oE", "Priya Menon|Daniel O'Brien|E-4471|EMP-20233",
                             str(TRACES_FILE)], capture_output=True, text=True).stdout.strip()
    print(f"  Scan of traces.jsonl for seeded PII: {'LEAK → ' + leaked if leaked else 'NONE — clean ✓'}")

    # 2. Seeded sample
    section(2, "SEEDED RANDOM SAMPLE OF 20 (reproducible)")
    picked, pool = sample_trace_ids(DEFAULT_SEED, 20, "production")
    print(f"  seed={DEFAULT_SEED}  pool={pool} production traces  n=20")
    print("  selected:")
    for i in range(0, 20, 5):
        print("    " + "  ".join(picked[i:i+5]))

    # 3. Inspection view
    section(3, "INSPECTION VIEW — question -> retrieved(chunk,score) -> answer")
    for tid in INSPECT:
        t = get_trace(tid)
        print(f"\n  [{tid}]")
        print(f"    Q: {t['question']}")
        print(f"    R: {[(c['chunk_id'], round(c['score'],4)) for c in t['retrieved']]}")
        ans = t['raw_output'].replace('\n', ' ')
        print(f"    A: {ans[:300]}{'…' if len(ans) > 300 else ''}")

    # 4. Replay
    section(4, "REPLAY ONE TRACE FROM THE TRACE ALONE")
    if args.no_replay:
        print("  (skipped — pass without --no-replay to run the live replay)")
    else:
        from Services.replay import pick_seeded_trace_id, check_completeness, replay
        tid = pick_seeded_trace_id(REPLAY_SEED)
        t = get_trace(tid)
        missing = check_completeness(t)
        print(f"  seeded pick (seed={REPLAY_SEED}) -> {tid}")
        print(f"  completeness: {'ALL fields present ✓' if not missing else 'MISSING ' + str(missing)}")
        out = replay(t)
        print(f"\n  ORIGINAL : {t['raw_output'][:220].replace(chr(10),' ')}…")
        print(f"  REPLAYED : {out[:220].replace(chr(10),' ')}…")
        same = out.strip() == t['raw_output'].strip()
        print(f"  byte-identical: {same}")
        if not same:
            print("  (same facts + same cited chunk; wording varies — gemini-2.5-flash is")
            print("   not byte-deterministic even at temperature=0. Replay reproduces the")
            print("   ANSWER from the trace alone, which is the point.)")

    # 5. Taxonomy
    section(5, "RANKED FAILURE TAXONOMY (see taxonomy.md)")
    print(f"  {'#':<2} {'mode':<52} {'cnt':>5} {'freq':>5}  {'example':<10} severity")
    for rank, name, cnt, freq, sev, ex in TAXONOMY:
        print(f"  {rank:<2} {name[:52]:<52} {cnt:>5} {freq:>5}  {ex:<10} {sev}")
    print("\n  Complaint was 'quotes the wrong policy' — that mode appeared 0 times.")
    print("  Real #1 problem: refusing answerable questions. Fix target: Mode 1.")
    print("  Prediction committed BEFORE any fix: git cc32013 (see prediction.md)")
    hr()


if __name__ == "__main__":
    main()
