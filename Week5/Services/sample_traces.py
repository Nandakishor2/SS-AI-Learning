"""
Week 5 — Seeded, provable RANDOM sample of 20 production traces.

The seed is printed and is the ONLY source of randomness, so anyone can rerun
this and get the identical 20 trace_ids. We sample ONLY from source=="production"
traffic — never the curated demo set, never "the ones we remember breaking".

    python -m Services.sample_traces            # default seed 20260601, n=20
    python -m Services.sample_traces --seed 7 --n 20
"""
import sys
import random
import argparse
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from Services.trace_logger import load_traces

DEFAULT_SEED = 20260601  # pasted in the write-up; change only with intent


def sample_trace_ids(seed: int = DEFAULT_SEED, n: int = 20, source: str = "production"):
    traces = load_traces(source=source)
    ids = sorted(t["trace_id"] for t in traces)   # deterministic base order
    if n > len(ids):
        raise ValueError(f"Asked for {n} but only {len(ids)} {source} traces exist.")
    rng = random.Random(seed)
    picked = sorted(rng.sample(ids, n))
    return picked, len(ids)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--source", default="production")
    args = ap.parse_args()

    picked, pool = sample_trace_ids(args.seed, args.n, args.source)
    print(f"SEED        = {args.seed}")
    print(f"SOURCE POOL = {args.source}  ({pool} traces)")
    print(f"SAMPLE SIZE = {args.n}")
    print(f"SELECTED    = {picked}")


if __name__ == "__main__":
    main()
