"""
Week 8 · THE trajectory eval — one command.

    python3.14 trajectory_eval.py              # live: runs v0/v1/v2, caches, writes report
    python3.14 trajectory_eval.py --offline    # reproduce from cache, no API key

It scores the agent's PATH, not just its answer, over the same 10 HR cases used in Week 7,
and prints:
  • the four trajectory numbers per variant — tool-choice accuracy, argument validity,
    step efficiency, and cost/question as p50 AND max (not a bare mean);
  • the OUTCOME-vs-TRAJECTORY GAP, with one named right-answer-wrong-path case;
  • the top failure mode's count BEFORE -> AFTER one mitigation, and the price it cost;
  • the per-mode regression table across the whole failure zoo.

Variants (see trajectory/variants.py for the full, honest rationale):
  v0_control   hardened Week-7 agent, no fast path — the clean reference.
  v1_baseline  + a get_quick_entitlement fast path & a latency prompt — the regression.
  v2_mitigated v1 + ONE change: a record-first argument-validation guard.
"""
import sys
import csv
import json
import statistics
from pathlib import Path

from agent_race.questions import QUESTIONS
from trajectory.capture import run_variant
from trajectory.expected import EXPECTED
from trajectory.score import analyze, ALL_MODES

HERE = Path(__file__).resolve().parent
OUT = HERE / "trajectory"


def numbers(analyses, records):
    n = len(analyses)
    calls = [chk for a in analyses for chk in a["arg_checks"]]
    valid_calls = sum(1 for _, ok, _ in calls)
    costs = [r["cost_usd"] for r in records]
    toks = [r["tokens"] for r in records]
    lat = [r["latency_ms"] for r in records]
    return {
        "tool_choice_accuracy": sum(a["seq_valid"] for a in analyses) / n,
        "argument_validity_rate": (valid_calls / len(calls)) if calls else 1.0,
        "step_efficiency_mean": statistics.mean(a["step_efficiency"] for a in analyses),
        "cost_p50": statistics.median(costs),
        "cost_max": max(costs),
        "tokens_total": sum(toks),
        "latency_p50": statistics.median(lat),
        "outcome_pass_rate": sum(a["outcome_pass"] for a in analyses) / n,
        "trajectory_pass_rate": sum(a["trajectory_pass"] for a in analyses) / n,
    }


def mode_counts(analyses):
    c = {m: 0 for m in ALL_MODES}
    for a in analyses:
        c[a["mode"]] = c.get(a["mode"], 0) + 1
    return c


def run(offline):
    variants = ["v0_control", "v1_baseline", "v2_mitigated"]
    data = {}
    for v in variants:
        print(f"\n=== {v} ({'offline' if offline else 'LIVE'}) ===")
        recs = run_variant(v, offline=offline)
        ana = [analyze(r) for r in recs]
        data[v] = {"records": recs, "analyses": ana,
                   "numbers": numbers(ana, recs), "modes": mode_counts(ana)}
    return data


def _fmt_seq(a):
    return " -> ".join(a["name_seq"]) or "(no tools)"


def report(data):
    v0, v1, v2 = data["v0_control"], data["v1_baseline"], data["v2_mitigated"]

    # ---- the four trajectory numbers, three columns -----------------------------
    print("\n" + "=" * 78)
    print("TRAJECTORY NUMBERS (same 10 HR cases)")
    print("-" * 78)
    hdr = f"{'metric':<30}{'v0 control':>15}{'v1 baseline':>16}{'v2 mitigated':>17}"
    print(hdr)
    rows = [
        ("tool-choice accuracy", "tool_choice_accuracy", "pct"),
        ("argument validity rate", "argument_validity_rate", "pct"),
        ("step efficiency (taken/needed)", "step_efficiency_mean", "x"),
        ("cost/question p50 ($)", "cost_p50", "usd"),
        ("cost/question MAX ($)", "cost_max", "usd"),
        ("outcome pass rate", "outcome_pass_rate", "pct"),
        ("trajectory pass rate", "trajectory_pass_rate", "pct"),
    ]
    for label, key, kind in rows:
        def cell(d):
            x = d["numbers"][key]
            if kind == "pct": return f"{x*100:.0f}%"
            if kind == "usd": return f"{x:.6f}"
            return f"{x:.2f}"
        print(f"{label:<30}{cell(v0):>15}{cell(v1):>16}{cell(v2):>17}")
    print("=" * 78)

    # ---- the gap + a named right-answer-wrong-path case -------------------------
    gap_v1 = v1["numbers"]["outcome_pass_rate"] - v1["numbers"]["trajectory_pass_rate"]
    print(f"\nOUTCOME-vs-TRAJECTORY GAP (v1 baseline): "
          f"{v1['numbers']['outcome_pass_rate']*100:.0f}% outcome "
          f"- {v1['numbers']['trajectory_pass_rate']*100:.0f}% trajectory "
          f"= {gap_v1*100:.0f} pts")
    rawp = [a for a in v1["analyses"] if a["right_answer_wrong_path"]]
    print(f"right-answer-wrong-path cases: {[a['qid'] for a in rawp] or 'none'}")
    if rawp:
        a = rawp[0]
        q = next(q for q in QUESTIONS if q["id"] == a["qid"])
        rec = next(r for r in v1["records"] if r["qid"] == a["qid"])
        print(f"  e.g. {a['qid']}: outcome PASS but trajectory FAIL ({a['mode']}).")
        print(f"       path taken : {_fmt_seq(a)}   (never read {EXPECTED[a['qid']]['employee_id']}'s record)")
        print(f"       answer     : {rec['answer'][:90]}")
        print(f"       why lucky  : the standard figure happens to match this employee's band.")

    # ---- top mode before -> after + price ---------------------------------------
    top_mode = max(v1["modes"], key=lambda m: (v1["modes"][m] if m != "clean" else -1))
    before, after = v1["modes"][top_mode], v2["modes"][top_mode]
    dtok = v2["numbers"]["tokens_total"] - v1["numbers"]["tokens_total"]
    dcost = v2["numbers"]["cost_p50"] - v1["numbers"]["cost_p50"]
    dlat = v2["numbers"]["latency_p50"] - v1["numbers"]["latency_p50"]
    print(f"\nMITIGATION — record-first guard (one change). Top mode '{top_mode}': "
          f"{before} -> {after}")
    print(f"  outcome pass {v1['numbers']['outcome_pass_rate']*100:.0f}% -> "
          f"{v2['numbers']['outcome_pass_rate']*100:.0f}%   "
          f"trajectory pass {v1['numbers']['trajectory_pass_rate']*100:.0f}% -> "
          f"{v2['numbers']['trajectory_pass_rate']*100:.0f}%")
    print(f"  PRICE PAID: +{dtok} tokens over 10 q, cost/q p50 +${dcost:.6f}, "
          f"latency p50 +{dlat:.0f} ms (the blocked fast path forces a re-plan).")

    # ---- per-mode regression table (req 5) --------------------------------------
    print("\nPER-MODE REGRESSION (v1 -> v2), every mode checked:")
    print(f"  {'mode':<20}{'v1':>5}{'v2':>5}   note")
    for m in ALL_MODES:
        b, af = v1["modes"][m], v2["modes"][m]
        note = ""
        if af > b and m != "clean":
            note = "<-- WORSE / new failures"
        elif m == "clean" and af < b:
            note = "(fewer clean — check)"
        print(f"  {m:<20}{b:>5}{af:>5}   {note}")
    worse = [m for m in ALL_MODES if m != "clean" and v2["modes"][m] > v1["modes"][m]]
    print(f"  => modes that got worse or appeared: {worse or 'NONE'}")

    # ---- persist ----------------------------------------------------------------
    _write_csv(data)
    summary = {v: {"numbers": data[v]["numbers"], "modes": data[v]["modes"]} for v in data}
    summary["gap_v1_pts"] = round(gap_v1 * 100, 1)
    summary["top_mode"] = top_mode
    summary["top_mode_before_after"] = [before, after]
    summary["price"] = {"delta_tokens_10q": dtok, "delta_cost_p50": round(dcost, 6),
                        "delta_latency_p50_ms": round(dlat, 1)}
    summary["right_answer_wrong_path_cases"] = [a["qid"] for a in rawp]
    (OUT / "trajectory_report.json").write_text(json.dumps(summary, indent=2))
    print(f"\nwrote {OUT/'trajectory_report.json'} and {OUT/'trajectory_eval.csv'}")


def _write_csv(data):
    with (OUT / "trajectory_eval.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["variant", "qid", "name_seq", "read_record", "args_valid",
                    "seq_valid", "trajectory_pass", "outcome_pass",
                    "right_answer_wrong_path", "mode", "steps_taken", "steps_needed",
                    "tokens", "cost_usd", "latency_ms", "stop_reason"])
        for v in data:
            recs = {r["qid"]: r for r in data[v]["records"]}
            for a in data[v]["analyses"]:
                r = recs[a["qid"]]
                w.writerow([v, a["qid"], " -> ".join(a["name_seq"]), a["read_record"],
                            a["args_valid"], a["seq_valid"], a["trajectory_pass"],
                            a["outcome_pass"], a["right_answer_wrong_path"], a["mode"],
                            a["steps_taken"], a["steps_needed"], r["tokens"], r["cost_usd"],
                            r["latency_ms"], r["stop_reason"]])


def main():
    offline = "--offline" in sys.argv[1:]
    print("WEEK 8 · TRAJECTORY EVAL — path, not just answer "
          f"({'offline replay' if offline else 'live run'})")
    data = run(offline)
    report(data)


if __name__ == "__main__":
    main()
