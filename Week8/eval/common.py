"""
Week 6 — shared helpers: load the eval set, and produce the app's answer for a
case by running the REAL pipeline live (Retrieve -> Prompt -> Generate).

Answers are snapshotted to eval/eval_answers.jsonl so that:
  * the blind hand-labels and the judge score the SAME frozen answers, and
  * re-runs / offline runs are reproducible and free.

Use `answers_for(cases, live=...)`:
  live=True  -> regenerate every answer through the app (needs Qdrant + API key),
                then overwrite the snapshot.
  live=False -> load the snapshot if present (no API/Qdrant needed).
  live=None  -> load snapshot if complete, else regenerate live (default).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVAL_SET = ROOT / "eval" / "eval_set.jsonl"
SNAPSHOT = ROOT / "eval" / "eval_answers.jsonl"


def load_cases() -> list[dict]:
    cases = []
    with open(EVAL_SET, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def _load_snapshot() -> dict:
    if not SNAPSHOT.exists():
        return {}
    out = {}
    with open(SNAPSHOT, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                r = json.loads(line)
                out[r["case_id"]] = r
    return out


def _save_snapshot(by_id: dict, order: list[str]) -> None:
    with open(SNAPSHOT, "w", encoding="utf-8") as fh:
        for cid in order:
            fh.write(json.dumps(by_id[cid], ensure_ascii=False) + "\n")


def _generate_live(case: dict) -> dict:
    # Imported lazily so offline runs never touch Qdrant / the API.
    from Services.rag_engine import answer_query
    res = answer_query(case["question"], region=case.get("region_filter"))
    return {
        "case_id": case["case_id"],
        "question": case["question"],
        "answer": res["answer"],
        "contexts": [
            {"chunk_id": c["chunk_id"], "policy_id": c["policy_id"],
             "region": c["region"], "effective_date": c.get("effective_date"),
             "text": c["text"]}
            for c in res["contexts"]
        ],
        "top_sources": [c["chunk_id"] for c in res["contexts"]],
    }


def answers_for(cases: list[dict], live=None) -> dict:
    """Return {case_id: answer_record}. See module docstring for `live`."""
    snap = _load_snapshot()
    complete = all(c["case_id"] in snap for c in cases)

    if live is False:
        if not complete:
            missing = [c["case_id"] for c in cases if c["case_id"] not in snap]
            raise RuntimeError(
                f"offline run but snapshot missing cases: {missing}. "
                f"Run once with --live to build eval/eval_answers.jsonl.")
        return {c["case_id"]: snap[c["case_id"]] for c in cases}

    if live is None and complete:
        return {c["case_id"]: snap[c["case_id"]] for c in cases}

    # live is True, or snapshot incomplete -> regenerate everything live.
    by_id = {}
    for c in cases:
        by_id[c["case_id"]] = _generate_live(c)
    _save_snapshot(by_id, [c["case_id"] for c in cases])
    return by_id
