"""
THE RACE: agent vs workflow over the SAME 10 questions. Writes race.csv and prints the
one comparable table of 8 numbers (4 per system): pass rate, p50 latency, total tokens,
cost per question.

    python3.14 -m agent_race.race            # live (also refreshes .race_cache.json)
    python3.14 -m agent_race.race --offline  # replay the cached run, no API calls
"""
import sys
import csv
import json
import statistics
from pathlib import Path

from agent_race.questions import QUESTIONS
from agent_race.scoring import passed
from agent_race.agent import run_agent
from agent_race.workflow import run_workflow

HERE = Path(__file__).resolve().parent
CACHE = HERE / ".race_cache.json"
CSV_OUT = HERE / "race.csv"


def _collect(offline: bool):
    if offline:
        if not CACHE.exists():
            sys.exit("No .race_cache.json — run once live first: python3.14 -m agent_race.race")
        rows = json.loads(CACHE.read_text())
        # Re-derive pass from the cached ANSWERS with the current scorer (answers are the
        # ground truth we cached; pass is just a function of them).
        exp = {q["id"]: q["expected"] for q in QUESTIONS}
        for r in rows:
            r["agent_pass"] = passed(r.get("agent_answer", ""), exp[r["qid"]])
            r["wf_pass"] = passed(r.get("wf_answer", ""), exp[r["qid"]])
        return rows

    rows = []
    for q in QUESTIONS:
        a = run_agent(q["question"])
        w = run_workflow(q["question"])
        rows.append({
            "qid": q["id"], "branching": q["branching"],
            "agent_pass": passed(a.answer, q["expected"]),
            "agent_latency_ms": round(a.latency_ms, 1),
            "agent_tokens": a.meter.total_tokens,
            "agent_cost_usd": round(a.meter.cost_usd, 6),
            "agent_laps": a.iters, "agent_stop": a.stop_reason,
            "wf_pass": passed(w.answer, q["expected"]),
            "wf_latency_ms": round(w.latency_ms, 1),
            "wf_tokens": w.meter.total_tokens,
            "wf_cost_usd": round(w.meter.cost_usd, 6),
            "agent_answer": a.answer, "wf_answer": w.answer,
        })
        print(f"  {q['id']}: agent pass={rows[-1]['agent_pass']} "
              f"({a.meter.total_tokens}t ${a.meter.cost_usd:.5f} {a.latency_ms:.0f}ms, {a.iters} laps) | "
              f"wf pass={rows[-1]['wf_pass']} ({w.meter.total_tokens}t ${w.meter.cost_usd:.5f} {w.latency_ms:.0f}ms)")
    CACHE.write_text(json.dumps(rows, indent=2))
    return rows


def _four_numbers(rows, prefix):
    n = len(rows)
    passes = sum(1 for r in rows if r[f"{prefix}_pass"])
    return {
        "pass_rate": passes / n,
        "p50_latency_ms": statistics.median(r[f"{prefix}_latency_ms"] for r in rows),
        "total_tokens": sum(r[f"{prefix}_tokens"] for r in rows),
        "cost_per_q_usd": sum(r[f"{prefix}_cost_usd"] for r in rows) / n,
    }


def main():
    offline = "--offline" in sys.argv[1:]
    print(f"RACE — agent vs workflow over {len(QUESTIONS)} questions "
          f"({'offline replay' if offline else 'live'})\n")
    rows = _collect(offline)

    # write per-question race.csv
    with CSV_OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "qid", "branching",
            "agent_pass", "agent_latency_ms", "agent_tokens", "agent_cost_usd", "agent_laps", "agent_stop",
            "wf_pass", "wf_latency_ms", "wf_tokens", "wf_cost_usd"])
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in w.fieldnames})

    agent = _four_numbers(rows, "agent")
    wf = _four_numbers(rows, "wf")

    print("\n" + "=" * 62)
    print(f"{'metric':<22}{'AGENT':>16}{'WORKFLOW':>16}")
    print("-" * 62)
    print(f"{'pass rate':<22}{agent['pass_rate']*100:>15.0f}%{wf['pass_rate']*100:>15.0f}%")
    print(f"{'p50 latency (ms)':<22}{agent['p50_latency_ms']:>16.0f}{wf['p50_latency_ms']:>16.0f}")
    print(f"{'total tokens (10 q)':<22}{agent['total_tokens']:>16d}{wf['total_tokens']:>16d}")
    print(f"{'cost / question ($)':<22}{agent['cost_per_q_usd']:>16.6f}{wf['cost_per_q_usd']:>16.6f}")
    print("=" * 62)

    factor = agent["cost_per_q_usd"] / wf["cost_per_q_usd"] if wf["cost_per_q_usd"] else float("nan")
    print(f"\nagent costs ~{factor:.1f}x the workflow per question; "
          f"agent total tokens {agent['total_tokens']/max(wf['total_tokens'],1):.1f}x.")
    print(f"per-question CSV -> {CSV_OUT}")

    # machine-readable summary for the README/VERDICT
    (HERE / "race_summary.json").write_text(json.dumps(
        {"agent": agent, "workflow": wf, "n": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
