"""
Week 5 — Generate a REAL trace population by running varied, realistic employee
questions through the live HR RAG app and logging a complete trace for each.

These are NOT pre-sorted into failure categories. They are a plausible slice of
real People-Ops inbox traffic: well-formed policy lookups, vague/overview asks,
questions that name a city instead of a region, multi-part asks, out-of-corpus
asks, nonexistent policy/section numbers, and a few messages carrying employee
PII (to exercise redaction). Whatever the app does with them is recorded as-is.

    python -m Services.generate_traces          # generate both pools (fresh file)
    python -m Services.generate_traces --append # keep existing traces, add more
"""
import sys
import time
import argparse
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from Services.rag_engine import answer_query
from Services.trace_logger import TRACES_FILE, new_trace_id

# --- Production traffic: unlabelled, varied, realistic. region=None (the app's
#     default, exactly as ask.py runs it) so retrieval must disambiguate. ------
PRODUCTION_QUESTIONS = [
    "Hi, this is Priya Menon (employee E-4471) in our Singapore office — how many annual leave days can I carry over into next year?",
    "My name is Daniel O'Brien, staff ID EMP-20233, based in London. If I'm off sick for 10 days, how much of my pay do I keep?",
    "I work in APAC. If I don't use all my annual leave this year, how many days roll over and when do the leftover ones expire?",
    "In North America, what parental leave does a primary caregiver with about two years of service qualify for?",
    "What does section 3 of HR-207 cover?",
    "Give me an overview of the carry-over rules.",
    "In the UK, if I'm sick for 9 days, what certification do I need and what happens to my pay after the first 4 weeks?",
    "ANZ, second year of service — how many personal leave days do I get and what's the carer's conversion cap?",
    "How many days of paid sabbatical leave do I get after 5 years of service?",
    "What's the remote work stipend for APAC engineers?",
    "Can I cash out unused pet bereavement leave under HR-208?",
    "What's the bereavement leave policy for an immediate family member in EMEA?",
    "What does HR-210 say about jury duty leave?",
    "Under HR-207 section 5, what's the sabbatical cap for EMEA staff?",
    "What's the difference in annual-leave carry-over caps between APAC and EMEA?",
    "How much parental leave do I get as a primary caregiver?",
    "How many sick days am I entitled to?",
    "Under HR-208 section 2.2 for our LATAM team, how many days of paternity leave does a non-birthing parent get?",
    "Under HR-209 section 2.1 for ANZ staff in year two, what's the annual personal leave and the carer's cap?",
    "Under HR-207 section 3.2, what is the carry-over cap for a Tier 1 probationary employee in APAC?",
    "For HR-209 in the UK, what sick pay applies once an absence passes 8 days?",
    "What is the secondary caregiver entitlement under HR-208 in North America, and what service is needed?",
    "When did HR-209 take effect for our ANZ offices?",
    "When does HR-207 become effective in EMEA?",
    "do probationary staff in apac get any carryover?? i'm tier 1",
    "Newborn on the way and I'm the non-birthing parent, based in Mexico City — do I get any paid time off?",
    "I'm in our Sydney office and need two days off sick next week — do I have to bring a medical certificate?",
    "I'm based in Berlin. How many annual leave days am I entitled to each year?",
    "Primary caregiver in LATAM with 8 months of service — how many weeks of paid leave do I get?",
    "I'm in Toronto and just had a baby as the primary caregiver with 3 years in — how many weeks paid and any unpaid extension?",
]

# --- Curated DEMO set: the clean, well-formed questions the team always shows at
#     the People-Ops review. For the bonus challenge. --------------------------
DEMO_QUESTIONS = [
    "Under HR-207 section 3.2, what is the carry-over cap for a Tier 1 probationary employee in APAC?",
    "Under HR-208 section 2.2 for LATAM, how many days of paternity leave does a non-birthing parent receive?",
    "Under HR-209 section 2.1 for ANZ staff in their second year, what is the personal leave and carer's cap?",
    "What is the annual leave entitlement for EMEA staff under HR-207?",
    "Under HR-209 for the UK, what certification and pay apply for an absence of 8 or more days?",
    "What paid leave does a primary caregiver with 2 years of service get in North America under HR-208?",
    "What is the secondary caregiver entitlement under HR-208 in North America?",
    "When did HR-209 take effect for ANZ?",
    "What is the standard annual-leave carry-over cap in APAC under HR-207?",
    "How many days of chronic-health consultation leave are approved per year for UK staff under HR-209?",
]


def run_pool(questions, source, start_index):
    total = len(questions)
    for i, q in enumerate(questions):
        tid = new_trace_id(start_index + i)
        preview = q[:68].replace("\n", " ")
        print(f"  [{source:10s}] {tid}  {preview}{'…' if len(q) > 68 else ''}")
        try:
            answer_query(q, region=None, retriever="hybrid", log=True, source=source, trace_id=tid)
        except Exception as e:
            print(f"      !! error on {tid}: {e}")
        time.sleep(0.3)  # gentle on the API
    return start_index + total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--append", action="store_true", help="keep existing traces.jsonl and append")
    args = ap.parse_args()

    if not args.append and TRACES_FILE.exists():
        TRACES_FILE.unlink()
        print(f"Removed existing {TRACES_FILE} (fresh run)")

    print(f"\nGenerating {len(PRODUCTION_QUESTIONS)} production + {len(DEMO_QUESTIONS)} demo traces...\n")
    idx = 1
    idx = run_pool(PRODUCTION_QUESTIONS, "production", idx)
    idx = run_pool(DEMO_QUESTIONS, "demo", idx)
    print(f"\nDone. Traces written to {TRACES_FILE}")


if __name__ == "__main__":
    main()
