import sys
import argparse
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from Services.usage_meter import (
    answer_metered, print_usage, print_usage_both, validate_retrieval_gap,
)

RETRIEVER_LABELS = {
    "cosine": "Dense Cosine (semantic / meaning-based)",
    "bm25": "BM25 (lexical / exact-keyword)",
    "hybrid": "Hybrid BM25 + Dense fused via RRF (k=60)",
}

def print_banner(retriever: str):
    print("\n" + "=" * 65)
    print("      GLOBAL HR LEAVE POLICY RAG ASSISTANT - INTERACTIVE CLI")
    print("=" * 65)
    print(f"Retriever: {RETRIEVER_LABELS.get(retriever, retriever)}")
    print("Ask any question across all regional leave policy documents.")
    print("Type 'exit' or 'q' anytime to quit.\n")

def print_validation(question: str, retriever: str = "hybrid"):
    """Trainer's question: the answer (e.g. '14 weeks') is in the handbook — why does
    it refuse? Prove it: production depth refuses, deeper retrieval recovers the
    answer-bearing chunk and the model answers. Only the retrieval depth changed."""
    v = validate_retrieval_gap(question, retriever=retriever, shallow_k=3, deep_k=10)
    print("\n🔬 VALIDATION — is the answer actually in the corpus?")
    print("=" * 65)
    print(f"   PRODUCTION retrieval (top_k={v['shallow_k']}):  "
          f"{'REFUSED ❌' if v['shallow_refused'] else 'answered ✅'}")
    print(f"      sources: {[s[0] for s in v['shallow_sources']]}")
    print(f"   DEEPER retrieval     (top_k={v['deep_k']}): "
          f"{'still refused ❌' if v['deep_refused'] else 'ANSWERED ✅'}")
    if not v["deep_refused"]:
        print("      answer now:")
        print(f"      {v['deep_answer']}")
    if v["recovered"]:
        print("\n   Answer-bearing chunk(s) that were BELOW the top-3 cutoff:")
        for r in v["recovered"]:
            print(f"      • rank {r['rank']:>2}: {r['chunk_id']} "
                  f"({r['policy']}/{r['region']}) contains \"{r['figure']}\"")
        print("\n   → The figure was in the corpus all along; top_k=3 ranked it out.")
        print("     The refusal is a RETRIEVAL gap, not a missing-data problem.")
    else:
        print("\n   (No figure-bearing chunk recovered even at depth — genuinely out of corpus.)")
    print("=" * 65)


def process_question(question: str, retriever: str = "hybrid",
                     judge: bool = True, judge_version: str = "v2",
                     validate: bool = False, both_judges: bool = False):
    print("\n" + "-" * 65)
    print(f"🔎 Searching across all regional policies  [retriever: {retriever}]...")
    print("-" * 65)

    # In --both-judges mode, if this question is a blind-labelled eval case, grade its
    # FROZEN answer (the exact one the human labelled) so the v1-vs-v2 comparison is
    # reproducible — a freshly generated answer's wording can swing the borderline
    # boundary verdict. Otherwise, generate and grade a live answer.
    frozen = None
    graded_note = None
    if both_judges:
        from Services.live_judge import human_label, frozen_case
        cid, _ = human_label(question)
        frozen = frozen_case(cid) if cid else None
        if frozen:
            graded_note = f"frozen evaluation answer for [{cid}] (the exact answer the human graded)"

    if frozen:
        answer, contexts, answer_meter = frozen["answer"], frozen["contexts"], None
    else:
        answer, contexts, answer_meter = answer_metered(question, retriever=retriever, top_k=3)
    result = {
        "answer": answer,
        "contexts": contexts,
        "top_sources": [(c["chunk_id"], c["policy_id"], c["region"]) for c in contexts],
    }

    print("\n📚 RETRIEVED SOURCES:")
    if result["top_sources"]:
        for i, (chunk_id, policy, reg) in enumerate(result["top_sources"], 1):
            print(f"   [{i}] Chunk: {chunk_id} | Policy: {policy} | Region: {reg}")
    else:
        print("   No matching source chunks found.")

    print("\n💬 ASSISTANT ANSWER:" + (f"  ({graded_note})" if graded_note else ""))
    print("-" * 65)
    print(result["answer"])
    print("-" * 65)

    if both_judges:
        # Grade the SAME answer with judge v1 AND v2, lined up against the human
        # label — shows whether iterating the judge actually helped.
        try:
            from Services.live_judge import evaluate_both, print_both_panel
            ev = evaluate_both(question, result)
            print_both_panel(ev, graded_note=graded_note)
            print_usage_both(answer_meter, ev["usage"].get("v1"), ev["usage"].get("v2"))
        except Exception as e:
            print(f"\n🟩 JUDGE v1 vs v2 unavailable: {e}")
    else:
        # Grade the answer live with the SAME judge + deterministic assertions
        # used offline in eval/run_eval.py (see Services/live_judge.py).
        judge_usage = None
        try:
            from Services.live_judge import evaluate_live, print_panel
            ev = evaluate_live(question, result, version=judge_version, run_judge=judge)
            print_panel(ev)
            judge_usage = ev.get("judge_usage")
        except Exception as e:
            print(f"\n🧪 QUALITY CHECK unavailable: {e}")
        # Log the usage (answer call + judge call).
        print_usage(answer_meter, judge_usage=judge_usage)

    # Trainer's "why can't it find 14 weeks?" — prove it is a retrieval gap.
    if validate:
        print_validation(question, retriever=retriever)

def interactive_loop(retriever: str = "hybrid", judge: bool = True,
                     judge_version: str = "v2", validate: bool = False,
                     both_judges: bool = False):
    print_banner(retriever)
    while True:
        try:
            print("\n" + "=" * 65)
            question = input("📝 Enter your question: ").strip()

            if not question:
                continue

            if question.lower() in ["exit", "quit", "q"]:
                print("\nGoodbye!\n")
                break

            process_question(question, retriever=retriever,
                             judge=judge, judge_version=judge_version,
                             validate=validate, both_judges=both_judges)

        except KeyboardInterrupt:
            print("\n\nSession ended by user. Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Error processing query: {e}")

def main():
    parser = argparse.ArgumentParser(description="Ask questions to Global HR Leave Policy RAG Assistant")
    parser.add_argument("question", nargs="?", type=str, help="Question to ask (optional; starts interactive mode if omitted)")
    parser.add_argument(
        "-r", "--retriever",
        choices=["cosine", "bm25", "hybrid"],
        default="hybrid",
        help="Retrieval method: cosine (dense only), bm25 (lexical only), or hybrid (BM25+Dense RRF, default)",
    )
    parser.add_argument(
        "--no-judge", dest="judge", action="store_false",
        help="Skip the live LLM judge (still shows the free deterministic checks).",
    )
    parser.add_argument(
        "--judge-version", choices=["v1", "v2"], default="v2",
        help="Which judge prompt to grade with (default: v2).",
    )
    parser.add_argument(
        "--validate", action="store_true",
        help="On a refusal, prove the answer IS in the corpus by retrieving deeper "
             "(top_k=10) — shows the refusal is a retrieval gap, not missing data.",
    )
    parser.add_argument(
        "--both-judges", dest="both_judges", action="store_true",
        help="Grade the answer with BOTH judge v1 and v2 against the human label — "
             "shows where iterating the judge fixed a disagreement.",
    )
    parser.set_defaults(judge=True)

    args = parser.parse_args()

    if args.question:
        process_question(args.question, retriever=args.retriever,
                         judge=args.judge, judge_version=args.judge_version,
                         validate=args.validate, both_judges=args.both_judges)
    else:
        interactive_loop(retriever=args.retriever,
                         judge=args.judge, judge_version=args.judge_version,
                         validate=args.validate, both_judges=args.both_judges)

if __name__ == "__main__":
    main()
