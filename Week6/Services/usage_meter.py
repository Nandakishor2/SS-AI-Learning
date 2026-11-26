"""
Week 6 — usage metering for ask.py.

Two jobs, both asked for in the demo:

  1. LOG THE USAGE.  rag_engine.answer_query throws response.usage_metadata away, so
     Week 6 could never show what a question cost. This re-runs the SAME retrieval +
     prompt + model call but keeps the usage. Week 6 makes TWO calls per question —
     the answer, and the judge that grades it — and this logs both plus the total.

  2. VALIDATE THE REFUSAL.  When the assistant refuses "primary caregiver, 2 years",
     the trainer's question is: the answer (Standard band = 14 weeks) IS in the
     handbook — why can't it find it? validate_retrieval_gap() proves it: ask once at
     the production depth (top_k=3, refuses) and once deeper (top_k=10). The deeper
     pass pulls in the eligibility-matrix chunk that holds "14 weeks" and the model
     answers. Same corpus, same model — only the retrieval depth changed. So the data
     was always there; top_k=3 ranked it out. The bug is retrieval, provably.
"""
import re
from dataclasses import dataclass

from Services.rag_engine import (
    client, GEN_MODEL, GEN_TEMPERATURE, SYSTEM_INSTRUCTION,
    retrieve_context, build_prompt,
)

# Gemini 2.5 Flash list price (USD per 1,000,000 tokens): input, then output.
PRICE_IN_PER_M = 0.30
PRICE_OUT_PER_M = 2.50


@dataclass
class Meter:
    calls: int = 0
    prompt_tokens: int = 0
    output_tokens: int = 0     # billed output = total - prompt (includes thinking)
    total_tokens: int = 0
    cost_usd: float = 0.0

    def add(self, usage) -> int:
        p = int(getattr(usage, "prompt_token_count", 0) or 0)
        t = int(getattr(usage, "total_token_count", 0) or 0)
        out = max(t - p, 0)
        self.calls += 1
        self.prompt_tokens += p
        self.output_tokens += out
        self.total_tokens += t
        self.cost_usd += (p / 1_000_000) * PRICE_IN_PER_M + (out / 1_000_000) * PRICE_OUT_PER_M
        return t


def _text(resp) -> str:
    try:
        return (resp.candidates[0].content.parts[0].text or "").strip()
    except (AttributeError, IndexError, TypeError):
        return (getattr(resp, "text", "") or "").strip()


def answer_metered(question: str, retriever: str = "hybrid", top_k: int = 3):
    """Retrieve -> prompt -> one metered model call. Returns (answer, contexts, meter)."""
    meter = Meter()
    contexts = retrieve_context(question, region=None, top_k=top_k, retriever=retriever)
    prompt = build_prompt(question, contexts)
    resp = client.models.generate_content(
        model=GEN_MODEL, contents=prompt,
        config={"system_instruction": SYSTEM_INSTRUCTION, "temperature": GEN_TEMPERATURE},
    )
    meter.add(resp.usage_metadata)
    return _text(resp), contexts, meter


_FIGURE = re.compile(r"\b\d+\s+(?:weeks?|days?|months?)\b", re.IGNORECASE)
_REFUSAL_HINT = "do not have sufficient information"


def validate_retrieval_gap(question: str, retriever: str = "hybrid",
                           shallow_k: int = 3, deep_k: int = 10) -> dict:
    """Prove the answer is in the corpus but ranked out of the top-k.

    Answers the question at production depth and at a deeper depth, and flags the
    answer-bearing chunks that only appear in the deeper pass.
    """
    shallow_ans, shallow_ctx, m_shallow = answer_metered(question, retriever, top_k=shallow_k)
    deep_ans, deep_ctx, m_deep = answer_metered(question, retriever, top_k=deep_k)

    shallow_ids = {c["chunk_id"] for c in shallow_ctx}
    # Chunks that were BELOW the production cutoff but carry an actual figure.
    recovered = []
    for rank, c in enumerate(deep_ctx, 1):
        if c["chunk_id"] in shallow_ids:
            continue
        m = _FIGURE.search(c["text"])
        if m:
            recovered.append({
                "rank": rank, "chunk_id": c["chunk_id"], "policy": c["policy_id"],
                "region": c["region"], "figure": m.group(0),
            })

    return {
        "shallow_k": shallow_k, "deep_k": deep_k,
        "shallow_answer": shallow_ans, "deep_answer": deep_ans,
        "shallow_refused": _REFUSAL_HINT in shallow_ans.lower(),
        "deep_refused": _REFUSAL_HINT in deep_ans.lower(),
        "shallow_sources": [(c["chunk_id"], c["policy_id"], c["region"]) for c in shallow_ctx],
        "deep_sources": [(c["chunk_id"], c["policy_id"], c["region"]) for c in deep_ctx],
        "recovered": recovered,
        "meter_shallow": m_shallow, "meter_deep": m_deep,
    }


def print_usage(answer_meter: Meter, judge_usage=None) -> None:
    """Week-6 usage: this week makes two model calls per question — the answer, and
    the judge that grades it. Both are shown, with the combined bill. (Week 6 only;
    no other week is referenced.)"""
    print("\n🟦 WEEK 6 USAGE — what this question cost")
    print("-" * 65)
    print(f"   model {GEN_MODEL} @ ${PRICE_IN_PER_M}/1M in, ${PRICE_OUT_PER_M}/1M out")
    a_tok = answer_meter.total_tokens
    a_cost = answer_meter.cost_usd
    print(f"   1) answer call : {a_tok:>6,} tok  ${a_cost:.6f}")
    if judge_usage is not None:
        jp = int(getattr(judge_usage, "prompt_token_count", 0) or 0)
        jt = int(getattr(judge_usage, "total_token_count", 0) or 0)
        j_out = max(jt - jp, 0)
        j_cost = (jp / 1_000_000) * PRICE_IN_PER_M + (j_out / 1_000_000) * PRICE_OUT_PER_M
        print(f"   2) judge call  : {jt:>6,} tok  ${j_cost:.6f}")
        print("   " + "-" * 44)
        print(f"   TOTAL          : {a_tok + jt:>6,} tok  ${a_cost + j_cost:.6f}")
    else:
        print("   (judge disabled — answer call only)")
    print("-" * 65)


def _usage_tok_cost(u):
    jp = int(getattr(u, "prompt_token_count", 0) or 0)
    jt = int(getattr(u, "total_token_count", 0) or 0)
    j_out = max(jt - jp, 0)
    return jt, (jp / 1_000_000) * PRICE_IN_PER_M + (j_out / 1_000_000) * PRICE_OUT_PER_M


def print_usage_both(answer_meter, v1_usage=None, v2_usage=None) -> None:
    """Usage when a question is graded by BOTH judges: (answer, if generated) +
    judge v1 + judge v2. answer_meter may be None when a frozen answer was graded."""
    print("\n🟦 WEEK 6 USAGE — this question cost (BOTH judges)")
    print("-" * 65)
    print(f"   model {GEN_MODEL} @ ${PRICE_IN_PER_M}/1M in, ${PRICE_OUT_PER_M}/1M out")
    if answer_meter is not None:
        tot_tok, tot_cost = answer_meter.total_tokens, answer_meter.cost_usd
        print(f"   1) answer    : {answer_meter.total_tokens:>6,} tok  ${answer_meter.cost_usd:.6f}")
    else:
        tot_tok, tot_cost = 0, 0.0
        print("   1) answer    :  (not regenerated — graded the frozen eval answer)")
    for label, u in (("2) judge v1", v1_usage), ("3) judge v2", v2_usage)):
        if u is None:
            continue
        jt, jcost = _usage_tok_cost(u)
        print(f"   {label} : {jt:>6,} tok  ${jcost:.6f}")
        tot_tok += jt
        tot_cost += jcost
    print("   " + "-" * 44)
    print(f"   TOTAL        : {tot_tok:>6,} tok  ${tot_cost:.6f}")
    print("-" * 65)
