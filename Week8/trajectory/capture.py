"""
Run one agent variant over the 10 questions and record the full TRAJECTORY of each —
the ordered tool calls with their arguments, plus outcome pass and the cost meter.

Live runs are cached to trajectory/.traj_cache_<variant>.json so the whole Week-8 eval
reproduces offline with no API key (same pattern as the Week-7 race cache).
"""
import json
from pathlib import Path

from agent_race.agent import run_agent
from agent_race.questions import QUESTIONS
from agent_race.scoring import passed
from trajectory.variants import VARIANTS

HERE = Path(__file__).resolve().parent


def _trajectory(run_log):
    """Flatten the per-lap agent log into an ordered list of tool calls."""
    calls = []
    for entry in run_log:
        if entry.get("action") == "tool_calls":
            for c in entry["calls"]:
                calls.append({"name": c["name"], "args": c.get("args", {}),
                              "blocked": bool(c.get("blocked"))})
    return calls


def run_variant(variant_key: str, offline: bool = False) -> list:
    cache = HERE / f".traj_cache_{variant_key}.json"
    if offline:
        if not cache.exists():
            raise SystemExit(f"No cache for {variant_key} — run live once first.")
        return json.loads(cache.read_text())

    cfg = VARIANTS[variant_key]
    records = []
    for q in QUESTIONS:
        r = run_agent(q["question"], system_prompt=cfg.get("system_prompt"),
                      gemini_tools=cfg["gemini_tools"], dispatch=cfg.get("dispatch"),
                      guard=cfg["guard"])
        traj = _trajectory(r.log)
        records.append({
            "qid": q["id"],
            "employee_id": q["employee_id"],
            "question": q["question"],
            "trajectory": traj,
            "tool_name_seq": [c["name"] for c in traj if not c["blocked"]],
            "outcome_pass": passed(r.answer, q["expected"]),
            "answer": r.answer,
            "laps": r.iters,
            "tokens": r.meter.total_tokens,
            "cost_usd": round(r.meter.cost_usd, 6),
            "latency_ms": round(r.latency_ms, 1),
            "stop_reason": r.stop_reason,
        })
        seq = " -> ".join(c["name"] + (":" + str(c["args"].get("jurisdiction") or c["args"].get("employee_id") or "")
                                        if c["args"] else "") + ("[BLOCKED]" if c["blocked"] else "")
                          for c in traj) or "(no tools)"
        print(f"  {q['id']} outcome={'P' if records[-1]['outcome_pass'] else 'F'} "
              f"laps={r.iters} {r.meter.total_tokens}t ${r.meter.cost_usd:.5f} | {seq}")
    cache.write_text(json.dumps(records, indent=2))
    return records


if __name__ == "__main__":
    import sys
    key = sys.argv[1] if len(sys.argv) > 1 else "v1_baseline"
    off = "--offline" in sys.argv
    print(f"=== capture {key} ({'offline' if off else 'LIVE'}) ===")
    run_variant(key, offline=off)
