"""
Week 7 — metered RAG answer paths for ask.py (the cost-cutting demo).

Problem this fixes: ask.py called rag_engine.answer_query, which does
`response.text.strip()` and DROPS response.usage_metadata — so the production path
could never show tokens or cost. Week 7's token/cost math already exists and is
trusted (agent_race/llm.py: Meter + the Gemini price table). This module reuses
BOTH — the same retrieval/prompt from rag_engine and the same Meter/pricing from
agent_race — to answer a question while metering every model call.

Two paths over the IDENTICAL retrieved context, so a demo viewer sees the lesson
Week 7 proved (agent 24,792 tok vs workflow 6,244 tok, same pass rate):

  answer_direct()     — ONE model call. The "fixed workflow" shape. What ask.py
                        should have been doing all along. This is the reduced cost.

  answer_roundabout() — a 3-lap reflexion loop (draft → self-critique → finalise)
                        that RE-SENDS the full policy context every lap. Same final
                        grounded answer, but it pays for the context ~3x. This is
                        the "roundabout agent" — adaptability the task never needed.

Both return (answer, Meter). The Meter is agent_race's, so cost is computed with
the exact same per-1M-token prices used in the race.
"""
from agent_race.llm import Meter, generate, PRICE_IN_PER_M, PRICE_OUT_PER_M
from Services.rag_engine import (
    retrieve_context, build_prompt, SYSTEM_INSTRUCTION,
)


def _text(resp) -> str:
    try:
        return (resp.candidates[0].content.parts[0].text or "").strip()
    except (AttributeError, IndexError, TypeError):
        return (getattr(resp, "text", "") or "").strip()


def answer_direct(question: str, contexts: list[dict]) -> tuple[str, Meter]:
    """One metered model call over the retrieved context — the workflow shape."""
    meter = Meter()
    prompt = build_prompt(question, contexts)
    resp = generate(prompt, SYSTEM_INSTRUCTION)
    meter.add(resp.usage_metadata)
    return _text(resp), meter


def answer_roundabout(question: str, contexts: list[dict]) -> tuple[str, Meter]:
    """Same answer, the expensive way: draft -> critique -> finalise, re-sending
    the whole context each lap. Mirrors an agent loop that re-pays for context it
    already has. Metered per lap, so the sum is the real bill."""
    meter = Meter()
    context_block = build_prompt(question, contexts)  # question + full context

    # Lap 1 — draft.
    draft_prompt = context_block + "\n\nWrite a first-draft answer now."
    r1 = generate(draft_prompt, SYSTEM_INSTRUCTION)
    meter.add(r1.usage_metadata)
    draft = _text(r1)

    # Lap 2 — self-critique, context re-sent in full.
    critique_prompt = (
        context_block
        + f"\n\nA DRAFT ANSWER was produced:\n{draft}\n\n"
        "Critique this draft ONLY against the context above: is every figure grounded, "
        "is each citation present and correct, is any claim unsupported? "
        "List the concrete fixes needed. Do not rewrite the answer yet."
    )
    r2 = generate(critique_prompt, SYSTEM_INSTRUCTION)
    meter.add(r2.usage_metadata)
    critique = _text(r2)

    # Lap 3 — finalise, context re-sent in full AGAIN.
    final_prompt = (
        context_block
        + f"\n\nDRAFT:\n{draft}\n\nCRITIQUE:\n{critique}\n\n"
        "Produce the FINAL answer, applying the critique and following all system rules."
    )
    r3 = generate(final_prompt, SYSTEM_INSTRUCTION)
    meter.add(r3.usage_metadata)
    return _text(r3), meter


def _fmt(m: Meter) -> str:
    return (f"{m.calls} call(s) | {m.total_tokens:,} tok "
            f"(in {m.prompt_tokens:,} / out {m.output_tokens:,}) | ${m.cost_usd:.6f}")


def print_cost(meter: Meter, label: str = "this answer") -> None:
    print(f"\n🟦 WEEK 7 ADD-ON · TOKEN / COST — what did this answer cost?  [{label}]")
    print("-" * 65)
    print(f"   model gemini-2.5-flash @ ${PRICE_IN_PER_M}/1M in, ${PRICE_OUT_PER_M}/1M out")
    print(f"   {_fmt(meter)}")
    print("-" * 65)


def print_comparison(round_meter: Meter, direct_meter: Meter) -> None:
    """Before -> after panel: the roundabout agent vs the single direct call."""
    rt, dt = round_meter.total_tokens, direct_meter.total_tokens
    rc, dc = round_meter.cost_usd, direct_meter.cost_usd
    tok_factor = rt / dt if dt else float("nan")
    tok_saved = (1 - dt / rt) * 100 if rt else 0.0
    cost_saved = (1 - dc / rc) * 100 if rc else 0.0

    print("\n🟦 WEEK 7 ADD-ON · COST COMPARISON — same question, same context, two strategies")
    print("=" * 65)
    print(f"   {'strategy':<26}{'calls':>6}{'tokens':>10}{'cost $':>12}")
    print("   " + "-" * 54)
    print(f"   {'roundabout agent (before)':<26}{round_meter.calls:>6}"
          f"{rt:>10,}{rc:>12.6f}")
    print(f"   {'direct workflow (after)':<26}{direct_meter.calls:>6}"
          f"{dt:>10,}{dc:>12.6f}")
    print("   " + "-" * 54)
    print(f"   reduction: {tok_saved:.0f}% fewer tokens, {cost_saved:.0f}% cheaper "
          f"(agent costs {tok_factor:.1f}x per answer)")
    print("=" * 65)
    print("   Same grounded answer either way — the extra laps re-pay for context")
    print("   the model already had. That adaptability bought nothing here.")
