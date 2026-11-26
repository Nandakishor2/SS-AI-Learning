"""
Week 6 — live quality panel for ask.py.

Point of this module: the AI-judge and the deterministic checks that Week 6 built
used to live ONLY in the offline harness (eval/run_eval.py), scoring stored traces
against the 25 human labels. A person using ask.py never saw them. This wires the
*same* code into the interactive path so the verdict shown when someone asks a
question is produced by the exact grader used offline — nothing is re-implemented
here, it only adapts an unlabeled live question into the shapes eval/ expects.

Two layers, mirroring the Week-6 judge/assertion split:

  1. DETERMINISTIC (eval/assertions.py + eval/corpus.py) — no model call, free:
       • citation resolution (assertion A1), and
       • refusal detection WITH canonical-string exactness. The exactness bit is
         what surfaces the "refused but then appended extra commentary" drift:
         the answer still *starts* with the canonical refusal (substring match =
         refusal) but is no longer *equal* to it. That deviation is exactly the
         failure judge_v2 was calibrated around.

  2. LLM-AS-JUDGE (eval/judge.py, judge_v2 prompt) — one PASS/FAIL + reason on the
     single subjective criterion, policy_correctness.

The judge makes a live model call (one per question). Use --no-judge to show only
the free deterministic layer.
"""
import json
from pathlib import Path

from eval.assertions import is_refusal, assert_section_resolves
from eval.corpus import REFUSAL_STRING
from eval.judge import (
    judge_prompt_path, _context_str, _fill, _parse_verdict, _client,
    JUDGE_MODEL, JUDGE_TEMPERATURE,
)

_ROOT = Path(__file__).resolve().parent.parent


def human_label(question: str):
    """If this EXACT question is one of the 29 blind-labelled eval cases, return
    (case_id, 'PASS'|'FAIL'); otherwise (None, None). The human label is the ground
    truth the two judges are measured against."""
    try:
        qmap = {}
        for line in (_ROOT / "eval" / "eval_set.jsonl").read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            qmap[r["question"].strip()] = r["case_id"]
        cid = qmap.get(question.strip())
        if not cid:
            return (None, None)
        labels = json.loads((_ROOT / "labels_25.json").read_text())["labels"]
        v = labels.get(cid)
        if v is None:
            return (cid, None)
        return (cid, "PASS" if v == 1 else "FAIL")
    except Exception:
        return (None, None)


def frozen_case(case_id: str):
    """Return the FROZEN evaluation answer + contexts for a case_id, from the
    eval_answers.jsonl snapshot (the exact answer the human labelled). Grading this
    fixed answer — instead of a freshly generated one — is what makes the v1-vs-v2
    comparison reproducible: the live answer's wording varies run-to-run and can swing
    the borderline boundary verdict, but the frozen answer does not."""
    if not case_id:
        return None
    try:
        for line in (_ROOT / "eval" / "eval_answers.jsonl").read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("case_id") == case_id:
                return {"answer": r["answer"], "contexts": r.get("contexts", [])}
    except Exception:
        pass
    return None


def _judge_metered(question: str, answer_record: dict, version: str):
    """Run the judge with the SAME prompt/model/parse as eval/judge.py, but keep the
    raw response so the call can be metered. Returns (verdict_dict, usage_metadata)."""
    template = judge_prompt_path(version).read_text()
    prompt = _fill(template, question, _context_str(answer_record), answer_record["answer"])
    resp = _client().models.generate_content(
        model=JUDGE_MODEL, contents=prompt, config={"temperature": JUDGE_TEMPERATURE},
    )
    verdict, reason = _parse_verdict(resp.text or "")
    return {"verdict": verdict, "reason": reason}, getattr(resp, "usage_metadata", None)


def _refusal_line(answer: str) -> tuple[str, str]:
    """Classify the answer's refusal status. Returns (status, detail)."""
    answer = (answer or "").strip()
    refusal = is_refusal(answer)                      # canonical sentence present?
    exact = answer.lower() == REFUSAL_STRING.strip().lower()
    if refusal and exact:
        return ("REFUSAL", "exact canonical refusal string")
    if refusal and not exact:
        return ("REFUSAL+DRIFT",
                "starts with the canonical refusal but appends extra commentary "
                "→ instruction drift (the judge_v2 target case)")
    return ("ANSWER", "substantive answer, not a refusal")


def evaluate_live(question: str, result: dict, version: str = "v2",
                  run_judge: bool = True) -> dict:
    """Grade one live (unlabeled) answer with the real eval code.

    `result` is the dict returned by Services.rag_engine.answer_query.
    """
    answer = result.get("answer", "")
    # eval/ expects a `case` (what we know about the question) and an
    # `answer_record` (what the assistant produced). Live questions carry no
    # human label, so `expected` is empty — assertions keyed on expected.* simply
    # report themselves not-applicable, which is correct.
    case = {"case_id": "live", "question": question, "expected": {}}
    answer_record = {"answer": answer, "contexts": result.get("contexts", [])}

    status, status_detail = _refusal_line(answer)

    # A1 — citation resolution (skipped automatically on a refusal).
    a1_applicable, a1_passed, a1_detail = assert_section_resolves(case, answer)

    out = {
        "refusal_status": status,
        "refusal_detail": status_detail,
        "a1": {"applicable": a1_applicable, "passed": a1_passed, "detail": a1_detail},
        "judge": None,
        "judge_usage": None,
        "judge_version": version,
    }

    if run_judge:
        try:
            # A fresh, metered judge call (no eval-cache read/write — live questions
            # must not pollute it). Reuses judge.py's prompt + parse verbatim.
            verdict, usage = _judge_metered(question, answer_record, version)
            out["judge"] = verdict
            out["judge_usage"] = usage
        except Exception as e:  # missing key, network, etc. — never crash ask.py
            out["judge"] = {"verdict": "UNAVAILABLE", "reason": repr(e)[:200]}

    return out


_ICON = {"PASS": "✅", "FAIL": "❌", "UNAVAILABLE": "⚠️", "ERROR": "⚠️"}


def print_panel(ev: dict) -> None:
    print("\n🟩 WEEK 6 ADD-ON · QUALITY CHECK — is this answer trustworthy?")
    print("   (the validated judge + assertions from eval/run_eval.py, now live)")
    print("-" * 65)
    print("   Deterministic checks (no model call):")
    print(f"     • Refusal     : {ev['refusal_status']}")
    print(f"                     {ev['refusal_detail']}")
    a1 = ev["a1"]
    if a1["applicable"]:
        tag = "PASS" if a1["passed"] else "FAIL"
        print(f"     • Citations A1: [{tag}] {a1['detail']}")
    else:
        print(f"     • Citations A1: n/a ({a1['detail']})")

    j = ev["judge"]
    if j is None:
        print("   LLM judge     : (disabled — run without --no-judge to grade)")
    else:
        v = j.get("verdict", "ERROR")
        icon = _ICON.get(v, "•")
        print(f"   LLM judge ({ev['judge_version']}): {icon} {v}")
        if j.get("reason"):
            print(f"                     reason: {j['reason']}")
    print("-" * 65)


def evaluate_both(question: str, result: dict) -> dict:
    """Grade the SAME answer with BOTH judge prompts (v1 and v2) and line them up
    against the human label. This is how you see whether iterating the judge helped:
    on the boundary case the human rejected, v1 wrongly PASSes and v2 correctly FAILs."""
    answer_record = {"answer": result.get("answer", ""), "contexts": result.get("contexts", [])}
    out = {"judges": {}, "usage": {}}
    for version in ("v1", "v2"):
        try:
            verdict, usage = _judge_metered(question, answer_record, version)
        except Exception as e:
            verdict, usage = {"verdict": "UNAVAILABLE", "reason": repr(e)[:150]}, None
        out["judges"][version] = verdict
        out["usage"][version] = usage
    cid, hlabel = human_label(question)
    out["case_id"] = cid
    out["human"] = hlabel
    return out


def print_both_panel(ev: dict, graded_note: str = None) -> None:
    v1 = ev["judges"]["v1"]
    v2 = ev["judges"]["v2"]
    human, cid = ev.get("human"), ev.get("case_id")
    a, b = v1.get("verdict"), v2.get("verdict")

    print("\n🟩 WEEK 6 · JUDGE v1  vs  JUDGE v2   (did iterating the judge help?)")
    print("-" * 65)
    if graded_note:
        print(f"   grading: {graded_note}")
    if human:
        tag = f" [{cid}]" if cid else ""
        print(f"   👤 HUMAN label{tag}: {human}      ← the ground truth")
    else:
        print("   👤 HUMAN label: (not one of the 29 blind-labelled cases)")
    for ver, j in (("v1", v1), ("v2", v2)):
        v = j.get("verdict", "ERROR")
        print(f"   ⚖️  Judge {ver}: {_ICON.get(v, '•')} {v}")
        if j.get("reason"):
            print(f"              {j['reason']}")

    print()
    if human and a != b:
        if b == human and a != human:
            print(f"   → Judge v1 was WRONG (said {a}, human said {human}). We fed that")
            print(f"     disagreement back into the prompt as a worked example, and Judge v2")
            print(f"     now AGREES with the human ({b}). The iteration fixed this case. ✅")
        elif a == human and b != human:
            print(f"   → Regression: v1 matched the human ({a}) but v2 diverged ({b}).")
        else:
            print(f"   → v1={a}, v2={b}, human={human}: they differ, neither matches.")
    elif a == b:
        print(f"   → v1 and v2 agree ({a}) here — the iteration changed nothing on this case.")
    print("-" * 65)
