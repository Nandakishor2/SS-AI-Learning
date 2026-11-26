import sys
import argparse
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from Services.rag_engine import retrieve_context
from Services.metered_rag import (
    answer_direct, answer_roundabout, print_cost, print_comparison,
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

def process_question(question: str, retriever: str = "hybrid", compare: bool = False):
    print("\n" + "-" * 65)
    print(f"🔎 Searching across all regional policies  [retriever: {retriever}]...")
    print("-" * 65)

    # Retrieve once; both answer strategies reuse the IDENTICAL context so the
    # only variable in the cost comparison is how many model calls are made.
    contexts = retrieve_context(question, region=None, top_k=3, retriever=retriever)
    top_sources = [(c["chunk_id"], c["policy_id"], c["region"]) for c in contexts]

    print("\n📚 RETRIEVED SOURCES:")
    if top_sources:
        for i, (chunk_id, policy, reg) in enumerate(top_sources, 1):
            print(f"   [{i}] Chunk: {chunk_id} | Policy: {policy} | Region: {reg}")
    else:
        print("   No matching source chunks found.")

    if compare:
        # Before -> after: answer the SAME question both ways, meter each.
        print("\n⏳ Running roundabout agent (3 laps) then direct workflow (1 call)...")
        round_answer, round_meter = answer_roundabout(question, contexts)
        direct_answer, direct_meter = answer_direct(question, contexts)

        print("\n💬 ASSISTANT ANSWER (direct workflow):")
        print("-" * 65)
        print(direct_answer)
        print("-" * 65)
        print_comparison(round_meter, direct_meter)
    else:
        # Default: the single metered call ask.py should always have shown.
        answer, meter = answer_direct(question, contexts)
        print("\n💬 ASSISTANT ANSWER:")
        print("-" * 65)
        print(answer)
        print("-" * 65)
        print_cost(meter, label="direct workflow — 1 call")

def interactive_loop(retriever: str = "hybrid", compare: bool = False):
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

            process_question(question, retriever=retriever, compare=compare)

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
        "--compare", action="store_true",
        help="Answer the same question two ways (roundabout agent vs direct workflow) "
             "and print the measured token/cost reduction.",
    )

    args = parser.parse_args()

    if args.question:
        process_question(args.question, retriever=args.retriever, compare=args.compare)
    else:
        interactive_loop(retriever=args.retriever, compare=args.compare)

if __name__ == "__main__":
    main()
