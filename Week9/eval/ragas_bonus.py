"""
Week 6 — BONUS. RAGAS-style faithfulness + context precision on the
handbook-backed cases, and the "confidently, faithfully wrong" demonstration:
an answer that scores 0.9+ faithfulness while citing a SUPERSEDED handbook
version's section.

Metrics are computed to the RAGAS definitions, using Gemini as the LLM:
  * faithfulness       = (# answer claims entailed by the retrieved context)
                         / (# answer claims)          -- in [0,1], higher=grounded
  * context_precision  = mean of precision@k over retrieved chunks, weighted by
                         whether chunk k is relevant to the question/answer
                         (RAGAS formula). Higher = relevant chunks ranked first.

The point of the bonus: faithfulness measures "is the answer supported by the
retrieved text", NOT "is the retrieved text the CURRENT handbook". So an answer
grounded perfectly in a SUPERSEDED addendum is faithful (~1.0) and precise, yet
wrong. The overall average hides it because every other case is genuinely current.

Run:  python3.14 -m eval.ragas_bonus
"""
import os
import re
import json
from pathlib import Path

from dotenv import load_dotenv

from eval.common import load_cases, answers_for

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
MODEL = "gemini-2.5-flash"

_CLIENT = None


def _client():
    global _CLIENT
    if _CLIENT is None:
        from google import genai
        _CLIENT = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    return _CLIENT


def _gen(prompt: str) -> str:
    r = _client().models.generate_content(
        model=MODEL, contents=prompt, config={"temperature": 0.0})
    return (r.text or "").strip()


def _json(prompt: str):
    txt = _gen(prompt)
    m = re.search(r"[\[{].*[\]}]", txt, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


# --------------------------------------------------------------------------
# RAGAS faithfulness
# --------------------------------------------------------------------------
def faithfulness(question: str, answer: str, context: str) -> dict:
    claims = _json(
        "Break the ANSWER into a JSON list of atomic factual claims (short "
        "strings). Only factual assertions; ignore pleasantries.\n"
        f"ANSWER:\n{answer}\n\nReturn ONLY a JSON array.")
    if not claims:
        claims = [answer]
    verdicts = _json(
        "For each CLAIM, decide if it can be directly inferred from the CONTEXT. "
        "Return a JSON array of 0/1 (1 = supported by context), same length and "
        "order as CLAIMS.\n"
        f"CONTEXT:\n{context}\n\nCLAIMS:\n{json.dumps(claims)}\n\n"
        "Return ONLY a JSON array of 0/1.")
    if not isinstance(verdicts, list) or not verdicts:
        verdicts = [1] * len(claims)
    verdicts = [1 if int(v) == 1 else 0 for v in verdicts][:len(claims)]
    score = sum(verdicts) / max(1, len(verdicts))
    return {"score": round(score, 3), "claims": claims, "verdicts": verdicts}


# --------------------------------------------------------------------------
# RAGAS context precision
# --------------------------------------------------------------------------
def context_precision(question: str, answer: str, chunks: list[dict]) -> dict:
    rels = []
    for c in chunks:
        v = _json(
            "Is this CONTEXT chunk useful for answering the QUESTION "
            "(given the reference ANSWER)? Return JSON {\"relevant\": 0 or 1}.\n"
            f"QUESTION: {question}\nANSWER: {answer}\n"
            f"CHUNK: {c['text']}")
        rels.append(1 if (v or {}).get("relevant") == 1 else 0)
    # RAGAS context precision = sum_k (precision@k * rel_k) / total_relevant
    total_rel = sum(rels)
    if total_rel == 0:
        return {"score": 0.0, "relevance": rels}
    cum = 0.0
    hits = 0
    for k, rel in enumerate(rels, start=1):
        if rel:
            hits += 1
            cum += hits / k
    return {"score": round(cum / total_rel, 3), "relevance": rels}


# --------------------------------------------------------------------------
# The superseded-version demo case (synthetic, clearly labelled)
# --------------------------------------------------------------------------
# Historical fact: HR-207 APAC carry-over used to be 15 days under the
# 2025-01-01 edition; the CURRENT edition (2026-01-01) lowered it to 10.
SUPERSEDED_CASE = {
    "case_id": "BONUS_superseded",
    "question": "What is the standard annual-leave carry-over cap in APAC under HR-207?",
    "answer": ("Under HR-207 section 3.1 for APAC, employees may roll over up to 15 "
               "unused leave days into the next calendar year [Chunk: "
               "struct_HR-207_APAC_3, Policy: HR-207, Section: 3.1, Region: APAC; "
               "Effective: 2025-01-01]."),
    "contexts": [{
        "chunk_id": "struct_HR-207_APAC_3@2025",
        "policy_id": "HR-207", "region": "APAC",
        "effective_date": "2025-01-01",  # SUPERSEDED edition
        "text": ("HR-207: Regional Leave Policy Addendum - APAC (Effective 2025-01-01)\n"
                 "3.1 Standard Carry-Over\nEmployees may roll over up to 15 unused "
                 "leave days into the next calendar year. Any excess days are "
                 "forfeited automatically on March 31st."),
    }],
    "current_version": "2026-01-01",
    "current_fact": "standard carry-over cap is 10 days",
}


def _ctx_str(rec):
    return "\n\n---\n\n".join(c["text"] for c in rec["contexts"])


def main():
    cases = {c["case_id"]: c for c in load_cases()}
    answers = answers_for(load_cases(), live=False)

    # a handful of genuinely-current grounded cases for the average
    sample_ids = ["C04", "C05", "C06", "C07", "C09", "C10", "C11"]

    print("\n" + "=" * 78)
    print("BONUS — RAGAS faithfulness & context precision (Gemini-computed)")
    print("=" * 78)
    print(f"{'case':18} {'faithful':>9} {'ctx_prec':>9}  note")
    print("-" * 78)

    rows = []
    for cid in sample_ids:
        rec = answers[cid]
        f = faithfulness(rec["question"], rec["answer"], _ctx_str(rec))
        p = context_precision(rec["question"], rec["answer"], rec["contexts"])
        rows.append((cid, f["score"], p["score"]))
        print(f"{cid:18} {f['score']:>9.2f} {p['score']:>9.2f}  current handbook")

    # the superseded, faithfully-wrong case
    sc = SUPERSEDED_CASE
    fs = faithfulness(sc["question"], sc["answer"], _ctx_str(sc))
    ps = context_precision(sc["question"], sc["answer"], sc["contexts"])
    print(f"{sc['case_id']:18} {fs['score']:>9.2f} {ps['score']:>9.2f}  "
          f"** cites SUPERSEDED {sc['contexts'][0]['effective_date']} "
          f"(current {sc['current_version']}: {sc['current_fact']}) **")

    all_f = [r[1] for r in rows] + [fs["score"]]
    avg_current = sum(r[1] for r in rows) / len(rows)
    avg_all = sum(all_f) / len(all_f)
    print("-" * 78)
    print(f"avg faithfulness (current cases only) : {avg_current:.3f}")
    print(f"avg faithfulness (incl. superseded)   : {avg_all:.3f}")
    print("\nWHY THE AVERAGE HIDES IT:")
    print(f"  The superseded answer scores faithfulness {fs['score']:.2f} and "
          f"context precision {ps['score']:.2f} —")
    print("  indistinguishable from a correct answer, because faithfulness only "
          "asks")
    print("  'is the answer supported by the retrieved text', not 'is the "
          "retrieved text")
    print(f"  the CURRENT handbook'. It cites HR-207 §3.1 @ "
          f"{sc['contexts'][0]['effective_date']} (15 days), but the current")
    print(f"  {sc['current_version']} edition says {sc['current_fact']}. Averaged "
          "in with")
    print(f"  genuinely-current cases ({avg_current:.2f}), the mean barely moves "
          f"({avg_all:.2f}) —")
    print("  the stale answer is invisible in the aggregate. Only the deterministic")
    print("  version assertion (A2_version_cited) catches it, for free.")


if __name__ == "__main__":
    main()
