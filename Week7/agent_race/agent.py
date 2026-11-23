"""
THE AGENT: a real tool-calling loop. The model decides which tool to call and when
to stop. Runnable alone:

    python3.14 -m agent_race.agent                 # run all 10 questions
    python3.14 -m agent_race.agent "Employee E002 ... ?"
    python3.14 -m agent_race.agent --demo-budget   # force a clean budget termination

ALL FOUR BUDGETS are checked EVERY lap (the task's whole point: an unchecked budget is
"a comment with ambition"). When any fires, the loop stops cleanly and returns what it
has, tagged with which budget tripped — it never spins.
"""
import sys
import time
import json
from dataclasses import dataclass
from google.genai import types

from agent_race import tools
from agent_race.llm import generate, Meter
from agent_race.questions import QUESTIONS, SYSTEM_PROMPT


# ---- The four budgets (all enforced below; edit to taste) ----------------------
MAX_ITERS = 6           # laps through the loop
MAX_TOKENS = 20_000     # cumulative tokens across all laps of ONE question
MAX_COST_USD = 0.02     # cumulative USD across all laps of ONE question
WALL_CLOCK_S = 30.0     # seconds from first lap


@dataclass
class RunResult:
    answer: str
    iters: int
    meter: Meter
    latency_ms: float
    stop_reason: str          # "answered" | "budget:max_iters" | "budget:max_tokens" | ...
    tool_calls: dict
    log: list                 # structured per-lap log lines


def run_agent(question: str,
              max_iters=MAX_ITERS, max_tokens=MAX_TOKENS,
              max_cost=MAX_COST_USD, wall_clock_s=WALL_CLOCK_S,
              verbose=False) -> RunResult:
    tools.reset_counts()
    meter = Meter()
    log = []
    t0 = time.perf_counter()
    contents = [types.Content(role="user", parts=[types.Part(text=question)])]
    answer, stop_reason = "", "answered"
    iters = 0

    while True:
        # ---- BUDGET GATE 1-4: check BEFORE spending another model call -----------
        elapsed = time.perf_counter() - t0
        if iters >= max_iters:
            stop_reason = "budget:max_iters"; break
        if meter.total_tokens >= max_tokens:
            stop_reason = "budget:max_tokens"; break
        if meter.cost_usd >= max_cost:
            stop_reason = "budget:max_cost"; break
        if elapsed >= wall_clock_s:
            stop_reason = "budget:wall_clock"; break

        iters += 1
        resp = generate(contents, SYSTEM_PROMPT, tools=tools.GEMINI_TOOLS)
        lap_tokens, lap_cost = meter.add(resp.usage_metadata)
        cand = resp.candidates[0]
        parts = cand.content.parts or []
        fcs = [p.function_call for p in parts if getattr(p, "function_call", None)]

        if not fcs:
            # Model produced a final text answer -> done.
            answer = next((p.text for p in parts if getattr(p, "text", None)), "")
            log.append({"lap": iters, "action": "final_answer",
                        "tokens": lap_tokens, "cum_tokens": meter.total_tokens,
                        "cum_cost": round(meter.cost_usd, 6)})
            break

        # Execute every requested tool call this lap, append results, loop again.
        contents.append(cand.content)
        tool_result_parts, lap_calls = [], []
        for fc in fcs:
            args = dict(fc.args)
            try:
                result = tools.DISPATCH[fc.name](args)
            except Exception as e:
                result = {"error": str(e)}
            lap_calls.append({"name": fc.name, "args": args})
            tool_result_parts.append(
                types.Part.from_function_response(name=fc.name, response={"result": result}))
        contents.append(types.Content(role="user", parts=tool_result_parts))
        log.append({"lap": iters, "action": "tool_calls", "calls": lap_calls,
                    "tokens": lap_tokens, "cum_tokens": meter.total_tokens,
                    "cum_cost": round(meter.cost_usd, 6),
                    "elapsed_s": round(time.perf_counter() - t0, 3)})
        if verbose:
            print(f"  lap {iters}: {[c['name'] for c in lap_calls]}  "
                  f"cum_tokens={meter.total_tokens} cum_cost=${meter.cost_usd:.5f}")

    latency_ms = (time.perf_counter() - t0) * 1000.0
    return RunResult(answer=answer, iters=iters, meter=meter, latency_ms=latency_ms,
                     stop_reason=stop_reason, tool_calls=dict(tools.CALL_COUNTS), log=log)


def _demo_budget():
    """Force a clean budget termination and write the log excerpt (task requirement).
    We set max_iters=2: these questions need >=2 tool laps + a compose lap, so the loop
    hits the iteration budget and terminates cleanly instead of spinning."""
    from pathlib import Path
    q = QUESTIONS[1]  # Q02 (needs record -> rules -> branch -> answer)
    print("=== BUDGET-TERMINATION DEMO ===")
    print(f"Question: {q['question']}")
    print("Budgets: MAX_ITERS=2 (tight), MAX_TOKENS=20000, MAX_COST=$0.02, WALL_CLOCK=30s\n")
    r = run_agent(q["question"], max_iters=2, verbose=True)
    lines = [
        "BUDGET-TERMINATION LOG",
        f"question: {q['question']}",
        "budgets: MAX_ITERS=2  MAX_TOKENS=20000  MAX_COST=0.02  WALL_CLOCK_S=30",
        "",
    ]
    for entry in r.log:
        lines.append(json.dumps(entry))
    lines += [
        "",
        f"STOP_REASON: {r.stop_reason}   <-- budget that fired",
        f"laps_used: {r.iters}/2",
        f"tokens_used: {r.meter.total_tokens}  cost_used: ${r.meter.cost_usd:.6f}  latency_ms: {r.latency_ms:.0f}",
        f"partial_answer: {r.answer!r}",
        "Loop terminated cleanly on the budget — it did NOT spin.",
    ]
    out = Path(__file__).resolve().parent / "logs" / "budget_termination.log"
    out.write_text("\n".join(lines) + "\n")
    print(f"\nSTOP_REASON = {r.stop_reason}  (laps {r.iters}/2)")
    print(f"Log written to {out}")


def _run_all():
    from agent_race.scoring import passed
    print(f"{'Q':<5}{'pass':<6}{'laps':<6}{'tokens':<8}{'cost$':<10}{'ms':<7}stop")
    for q in QUESTIONS:
        r = run_agent(q["question"])
        ok = passed(r.answer, q["expected"])
        print(f"{q['id']:<5}{str(ok):<6}{r.iters:<6}{r.meter.total_tokens:<8}"
              f"{r.meter.cost_usd:<10.6f}{r.latency_ms:<7.0f}{r.stop_reason}")


def main():
    args = sys.argv[1:]
    if args and args[0] == "--demo-budget":
        _demo_budget()
    elif args:
        r = run_agent(args[0], verbose=True)
        print("\nANSWER:", r.answer)
        print(f"stop={r.stop_reason} laps={r.iters} tokens={r.meter.total_tokens} "
              f"cost=${r.meter.cost_usd:.6f} latency={r.latency_ms:.0f}ms tool_calls={r.tool_calls}")
    else:
        _run_all()


if __name__ == "__main__":
    main()
