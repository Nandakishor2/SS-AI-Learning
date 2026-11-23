"""
Week 6 — THE one command. Runs the whole eval over 25+ mode-tagged cases
(including the real regression cases) and prints PASS RATE BY MODE.

For every case:
    1. produce the app's answer LIVE (Retrieve -> Prompt -> Generate),
    2. run the deterministic assertions (section resolves / version cited /
       notice numeric / refusal path),
    3. run the LLM judge on its single binary criterion (policy_correctness),
    4. case PASS  <=>  all applicable assertions pass AND judge == PASS.

Usage:
    python3.14 -m eval.run_eval                 # live answers + judge v1 (default)
    python3.14 -m eval.run_eval --judge v2      # use the iterated judge
    python3.14 -m eval.run_eval --offline       # reuse snapshot + cached verdicts
"""
import argparse
from collections import defaultdict

from eval.common import load_cases, answers_for
from eval.assertions import run_assertions, ASSERTIONS, JUDGED_CRITERIA
from eval.judge import judge_all


def main():
    ap = argparse.ArgumentParser(description="Week 6 one-command eval")
    ap.add_argument("--judge", default="v1", choices=["v1", "v2"],
                    help="which judge prompt to use (default v1)")
    ap.add_argument("--offline", action="store_true",
                    help="reuse the frozen answer snapshot + cached judge verdicts")
    ap.add_argument("--live", action="store_true",
                    help="force regenerating every answer through the app")
    args = ap.parse_args()

    cases = load_cases()
    live = True if args.live else (False if args.offline else None)
    answers = answers_for(cases, live=live)
    verdicts = judge_all(cases, answers, version=args.judge, offline=args.offline)

    by_mode = defaultdict(lambda: {"pass": 0, "total": 0, "fail_ids": []})
    rows = []
    for c in cases:
        cid = c["case_id"]
        ans = answers[cid]
        a = run_assertions(c, ans["answer"])
        jv = verdicts[cid]["verdict"]
        case_pass = a["_assertions_passed"] and jv == "PASS"
        by_mode[c["mode"]]["total"] += 1
        if case_pass:
            by_mode[c["mode"]]["pass"] += 1
        else:
            by_mode[c["mode"]]["fail_ids"].append(cid)
        # which assertions failed (for the per-case line)
        failed_asserts = [n for n, r in a.items()
                          if n in ASSERTIONS and r["applicable"] and r["passed"] is False]
        rows.append((cid, c["mode"], c["regression"], case_pass, jv, failed_asserts))

    # ---- per-case ----------------------------------------------------------
    print("\n" + "=" * 78)
    print(f"WEEK 6 EVAL  |  judge={args.judge}  |  {'OFFLINE' if args.offline else 'LIVE'}"
          f"  |  {len(cases)} cases")
    print("=" * 78)
    print(f"{'case':5} {'mode':26} {'reg':3} {'judge':5} {'result':6}  notes")
    print("-" * 78)
    for cid, mode, reg, cpass, jv, fa in rows:
        note = "" if cpass else ("assert:" + ",".join(fa) if fa else "judge:FAIL")
        print(f"{cid:5} {mode:26} {'Y' if reg else ' ':3} {jv:5} "
              f"{'PASS' if cpass else 'FAIL':6}  {note}")

    # ---- pass rate by mode -------------------------------------------------
    print("\n" + "=" * 78)
    print("PASS RATE BY MODE")
    print("=" * 78)
    print(f"{'mode':28} {'pass/total':>12} {'rate':>7}   failing")
    print("-" * 78)
    total_p = total_t = 0
    for mode in sorted(by_mode):
        d = by_mode[mode]
        total_p += d["pass"]; total_t += d["total"]
        rate = 100.0 * d["pass"] / d["total"]
        fails = ",".join(d["fail_ids"]) if d["fail_ids"] else "-"
        print(f"{mode:28} {d['pass']:>5}/{d['total']:<6} {rate:>6.0f}%   {fails}")
    print("-" * 78)
    overall = 100.0 * total_p / total_t
    print(f"{'OVERALL':28} {total_p:>5}/{total_t:<6} {overall:>6.1f}%")
    worst = min(by_mode, key=lambda m: by_mode[m]["pass"] / by_mode[m]["total"])
    wrate = 100.0 * by_mode[worst]["pass"] / by_mode[worst]["total"]
    print(f"\nNote: the OVERALL {overall:.1f}% hides the per-mode floor "
          f"(lowest: {worst} at {wrate:.0f}%). Read the modes, not the average.")

    # ---- assertion vs judged-criteria count --------------------------------
    print("\n" + "=" * 78)
    print("CRITERIA SPLIT (requirement 2)")
    print("=" * 78)
    print(f"Deterministic assertions : {len(ASSERTIONS)}  -> {', '.join(ASSERTIONS)}")
    print(f"Judged criteria          : {len(JUDGED_CRITERIA)}  -> {', '.join(JUDGED_CRITERIA)}")
    regs = [cid for cid, _, reg, *_ in rows if reg]
    print(f"\nRegression cases (verbatim replays): {len(regs)} -> {', '.join(regs)}")


if __name__ == "__main__":
    main()
