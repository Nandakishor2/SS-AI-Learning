"""
THE WORKFLOW: the identical task as three hard-coded steps. Same inputs (the question
string), same tools (get_employee_record / get_jurisdiction_rules / search_handbook),
same model + output contract, same scoring. The ONLY difference from the agent is that
Python — not the model — fixes the order, and there is NO loop and NO function-calling.

    python3.14 -m agent_race.workflow                  # run all 10
    python3.14 -m agent_race.workflow "Employee E002 ... ?"

Steps:
  1. parse employee_id from the question  -> get_employee_record
  2.                                       -> get_jurisdiction_rules(record.jurisdiction)
  3. branch on the record to pick the band -> search_handbook for the citing section,
     then ONE plain model call composes the answer in the shared output contract.

Exactly one model call per question, no tools exposed to it: no loop hiding inside.
"""
import re
import sys
import time
from dataclasses import dataclass
from google.genai import types

from agent_race import tools
from agent_race.llm import generate, Meter
from agent_race.questions import QUESTIONS, SYSTEM_PROMPT


@dataclass
class RunResult:
    answer: str
    meter: Meter
    latency_ms: float
    stop_reason: str
    tool_calls: dict
    facts: dict


def _select_band(record: dict, rules: dict) -> dict:
    """STEP 3 branch — the path that depends on STEP 2's findings, in plain code."""
    tenure = record.get("tenure_months", 0)
    if "absence_bands" in rules:  # UK sick: branch on the planned absence duration
        days = record.get("planned_absence_days") or 0
        for b in rules["absence_bands"]:
            lo, hi = b["min_days"], b.get("max_days")
            if days >= lo and (hi is None or days <= hi):
                return b
        return rules["absence_bands"][-1]
    # tenure_bands: pick by tenure, honouring tier for APAC probation bands
    for b in rules["tenure_bands"]:
        lo = b.get("min_months", 0)
        hi = b.get("max_months")
        in_range = tenure >= lo and (hi is None or tenure < hi)
        if not in_range:
            continue
        if b.get("tier") and b["tier"] not in ("any",) and b["tier"] != record.get("tier"):
            continue
        return b
    return rules["tenure_bands"][-1]


def run_workflow(question: str) -> RunResult:
    tools.reset_counts()
    meter = Meter()
    t0 = time.perf_counter()

    # STEP 1 — employee record (no model call) --------------------------------
    m = re.search(r"\bE\d{3}\b", question)
    employee_id = m.group(0) if m else ""
    record = tools.get_employee_record(employee_id)

    # STEP 2 — jurisdiction rules (no model call) -----------------------------
    rules = tools.get_jurisdiction_rules(record.get("jurisdiction", ""))

    # STEP 3 — branch, then fetch the citing prose (no model call) ------------
    band = _select_band(record, rules)
    passages = tools.search_handbook(question, record.get("jurisdiction"))

    facts = {"record": record, "rules_meta": {k: rules.get(k) for k in ("policy_id", "section", "domain")},
             "selected_band": band,
             "handbook": [{"section": p["section"], "title": p["title"]} for p in passages]}

    # Single compose call — no tools, no loop. Same output contract as the agent.
    compose_prompt = (
        f"EMPLOYEE QUESTION:\n{question}\n\n"
        f"FACTS GATHERED BY THE WORKFLOW (authoritative — use these, do not change figures):\n"
        f"- employee: {record}\n"
        f"- governing policy: {facts['rules_meta']}\n"
        f"- the matching band for THIS employee: {band}\n"
        f"- handbook sections: {facts['handbook']}\n\n"
        f"Write the final answer now, following the output contract."
    )
    contents = [types.Content(role="user", parts=[types.Part(text=compose_prompt)])]
    resp = generate(contents, SYSTEM_PROMPT, tools=None)
    meter.add(resp.usage_metadata)
    answer = (resp.candidates[0].content.parts[0].text or "").strip()

    latency_ms = (time.perf_counter() - t0) * 1000.0
    return RunResult(answer=answer, meter=meter, latency_ms=latency_ms,
                     stop_reason="answered", tool_calls=dict(tools.CALL_COUNTS), facts=facts)


def _run_all():
    from agent_race.scoring import passed
    print(f"{'Q':<5}{'pass':<6}{'tokens':<8}{'cost$':<10}{'ms':<7}tool_calls")
    for q in QUESTIONS:
        r = run_workflow(q["question"])
        ok = passed(r.answer, q["expected"])
        print(f"{q['id']:<5}{str(ok):<6}{r.meter.total_tokens:<8}"
              f"{r.meter.cost_usd:<10.6f}{r.latency_ms:<7.0f}{r.tool_calls}")


def main():
    args = sys.argv[1:]
    if args:
        r = run_workflow(args[0])
        print("ANSWER:", r.answer)
        print(f"tokens={r.meter.total_tokens} cost=${r.meter.cost_usd:.6f} "
              f"latency={r.latency_ms:.0f}ms tool_calls={r.tool_calls}")
    else:
        _run_all()


if __name__ == "__main__":
    main()
