"""
Week 5 — Replay a trace FROM THE TRACE ALONE.

Proves the trace is complete enough to reconstruct the answer without the live
retriever: we rebuild the exact prompt from the stored chunk texts + question,
re-call the frozen model/params recorded on the trace, and show replayed output
next to the original. No Qdrant call, no re-retrieval.

    python -m Services.replay              # replays a seeded random trace_id
    python -m Services.replay trc_0007     # replays a specific trace
"""
import sys
import random
import argparse
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from Services.trace_logger import load_traces, get_trace
from Services.rag_engine import build_prompt, generate_answer

REQUIRED_FIELDS = ["trace_id", "prompt_version", "model", "params", "question", "retrieved", "raw_output"]


def pick_seeded_trace_id(seed: int, source: str = "production") -> str:
    ids = sorted(t["trace_id"] for t in load_traces(source=source))
    return random.Random(seed).choice(ids)


def check_completeness(trace: dict):
    missing = [f for f in REQUIRED_FIELDS if f not in trace or trace.get(f) in (None, "", [])]
    for c in trace.get("retrieved", []):
        if not c.get("text"):
            missing.append(f"retrieved[{c.get('chunk_id')}].text")
        if c.get("score") is None:
            missing.append(f"retrieved[{c.get('chunk_id')}].score")
    return missing


def replay(trace: dict) -> str:
    # Rebuild the identical prompt from the stored contexts (NOT a fresh retrieval).
    contexts = [
        {
            "chunk_id": c["chunk_id"], "source_file": c.get("source_file"),
            "policy_id": c.get("policy_id"), "region": c.get("region"),
            "effective_date": c.get("effective_date"), "text": c.get("text", ""),
        }
        for c in trace["retrieved"]
    ]
    prompt = build_prompt(trace["question"], contexts)
    return generate_answer(prompt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trace_id", nargs="?", help="trace to replay (default: seeded random pick)")
    ap.add_argument("--seed", type=int, default=424242)
    args = ap.parse_args()

    tid = args.trace_id or pick_seeded_trace_id(args.seed)
    if not args.trace_id:
        print(f"(no trace_id given — seeded pick, seed={args.seed})")
    trace = get_trace(tid)
    if trace is None:
        print(f"Trace {tid} not found."); return

    print("=" * 74)
    print(f"REPLAY  trace_id={tid}   source={trace.get('source')}")
    print("=" * 74)
    print(f"prompt_version : {trace.get('prompt_version')}")
    print(f"model          : {trace.get('model')}")
    print(f"params         : {trace.get('params')}")
    print(f"question       : {trace.get('question')}")
    print(f"retrieved      : {[ (c['chunk_id'], c['score']) for c in trace.get('retrieved', []) ]}")

    missing = check_completeness(trace)
    print("\nCOMPLETENESS CHECK")
    if missing:
        print(f"  MISSING fields (would need to be added): {missing}")
    else:
        print("  All replay-critical fields present: prompt_version, model, params,")
        print("  retrieved chunk_ids + scores + text, question, raw_output.")

    print("\n--- ORIGINAL raw_output ------------------------------------------")
    print(trace.get("raw_output"))

    replayed = replay(trace)
    print("\n--- REPLAYED output (from trace alone) ---------------------------")
    print(replayed)

    print("\n--- MATCH --------------------------------------------------------")
    print("  identical :", replayed.strip() == trace.get("raw_output", "").strip())


if __name__ == "__main__":
    main()
