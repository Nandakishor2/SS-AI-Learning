"""
Week 6 — Judge validation. Compares the LLM judge's verdicts on the single binary
criterion against the BLIND human labels (labels_25.json), and reports agreement.

The human labels were committed BEFORE any judge run (git order is the proof), so
this is validation, not "agreeing with yourself with extra steps".

Usage:
    python3.14 -m eval.validate_judge --version v1     # agreement_before
    python3.14 -m eval.validate_judge --version v2     # agreement_after
    python3.14 -m eval.validate_judge --both           # before -> after + disagreements
"""
import json
import argparse
from pathlib import Path

from eval.common import load_cases, answers_for
from eval.judge import judge_all

ROOT = Path(__file__).resolve().parent.parent
LABELS = ROOT / "labels_25.json"


def human_labels() -> dict:
    data = json.loads(LABELS.read_text())
    # 1 = PASS, 0 = FAIL  ->  "PASS"/"FAIL"
    return {k: ("PASS" if v == 1 else "FAIL") for k, v in data["labels"].items()}


def evaluate(version: str, offline: bool):
    cases = load_cases()
    answers = answers_for(cases, live=False if offline else None)
    verdicts = judge_all(cases, answers, version=version, offline=offline)
    human = human_labels()

    rows, agree = [], 0
    for c in cases:
        cid = c["case_id"]
        h = human[cid]
        j = verdicts[cid]["verdict"]
        ok = (h == j)
        agree += ok
        rows.append({
            "case_id": cid, "mode": c["mode"], "regression": c["regression"],
            "human": h, "judge": j, "agree": ok,
            "judge_reason": verdicts[cid].get("reason", ""),
            "question": c["question"], "answer": answers[cid]["answer"],
        })
    pct = 100.0 * agree / len(cases)
    return rows, agree, len(cases), pct


def print_table(rows, version, pct, agree, n):
    print("\n" + "=" * 78)
    print(f"JUDGE VALIDATION — {version}   agreement = {agree}/{n} = {pct:.1f}%")
    print("=" * 78)
    print(f"{'case':5} {'mode':26} {'human':5} {'judge':5} {'ok':3}  judge_reason")
    print("-" * 78)
    for r in rows:
        print(f"{r['case_id']:5} {r['mode']:26} {r['human']:5} {r['judge']:5} "
              f"{'=' if r['agree'] else 'X':3}  {r['judge_reason'][:40]}")
    dis = [r for r in rows if not r["agree"]]
    print("-" * 78)
    print(f"disagreements: {len(dis)} -> {', '.join(r['case_id'] for r in dis)}")
    return dis


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="v1", choices=["v1", "v2"])
    ap.add_argument("--both", action="store_true",
                    help="run v1 and v2, report before->after")
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()

    if args.both:
        r1, a1, n, p1 = evaluate("v1", args.offline)
        dis1 = print_table(r1, "v1", p1, a1, n)
        r2, a2, _, p2 = evaluate("v2", args.offline)
        dis2 = print_table(r2, "v2", p2, a2, n)

        (ROOT / "agreement_before.txt").write_text(
            f"{p1:.1f}% ({a1}/{n})  judge=v1\n")
        (ROOT / "agreement_after.txt").write_text(
            f"{p2:.1f}% ({a2}/{n})  judge=v2\n")

        print("\n" + "=" * 78)
        print(f"AGREEMENT BEFORE -> AFTER :  {p1:.1f}%  ->  {p2:.1f}%   "
              f"(delta {p2 - p1:+.1f} pts)")
        print("=" * 78)

        # dump disagreements for the iteration + analysis
        report = {
            "agreement_before": {"pct": p1, "agree": a1, "n": n, "version": "v1"},
            "agreement_after": {"pct": p2, "agree": a2, "n": n, "version": "v2"},
            "v1_disagreements": [
                {k: r[k] for k in ("case_id", "mode", "human", "judge",
                                   "judge_reason", "question", "answer")}
                for r in dis1],
            "v2_disagreements": [
                {k: r[k] for k in ("case_id", "mode", "human", "judge",
                                   "judge_reason")}
                for r in dis2],
        }
        (ROOT / "eval" / "disagreements.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False))
        print("\nwrote agreement_before.txt, agreement_after.txt, "
              "eval/disagreements.json")
    else:
        rows, agree, n, pct = evaluate(args.version, args.offline)
        dis = print_table(rows, args.version, pct, agree, n)
        tag = "before" if args.version == "v1" else "after"
        (ROOT / f"agreement_{tag}.txt").write_text(
            f"{pct:.1f}% ({agree}/{n})  judge={args.version}\n")
        # expose v1 disagreements for few-shot selection
        if args.version == "v1":
            (ROOT / "eval" / "disagreements.json").write_text(json.dumps({
                "v1_disagreements": [
                    {k: r[k] for k in ("case_id", "mode", "human", "judge",
                                       "judge_reason", "question", "answer")}
                    for r in dis]}, indent=2, ensure_ascii=False))
        print(f"\nwrote agreement_{tag}.txt")


if __name__ == "__main__":
    main()
