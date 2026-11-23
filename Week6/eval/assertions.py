"""
Week 6 — Deterministic assertions (the criteria pulled OUT of the LLM judge).

Requirement 2: *"Move at least 2 criteria out of the judge and into deterministic
assertions ... and delete those criteria from the judge prompt."*

Four criteria that used to be (or would naively be) handed to the judge are done
here instead, with `if` + a lookup table. They are cheap, reproducible, and never
have an off day:

    A1  section_resolves      — every [Chunk:.., Policy:.., Section:.., Region:..]
                                citation resolves to a section that REALLY EXISTS
                                in that (policy, region) addendum.
    A2  version_cited         — a handbook-version question cites the CURRENT
                                effective date for that (policy, region), and not
                                a mangled/absent one.
    A3  notice_period_numeric — a certification / notice-window answer contains an
                                actual numeric figure (days/weeks), not prose.
    A4  refusal_path          — an out-of-jurisdiction / out-of-corpus question
                                triggers the EXACT refusal string.

Each assertion returns (applicable, passed, detail). `applicable=False` means the
assertion does not pertain to this case and is skipped (not counted as a failure).
"""
import re

from eval.corpus import (
    VALID_POLICIES,
    VALID_REGIONS,
    REFUSAL_STRING,
    section_exists,
    current_version,
)

# [Chunk: struct_HR-207_APAC_3, Policy: HR-207, Section: 3.2, Region: APAC]
_CITATION_RE = re.compile(
    r"\[Chunk:\s*(?P<chunk>[^,\]]+),\s*"
    r"Policy:\s*(?P<policy>HR-\d+),\s*"
    r"Section:\s*(?P<section>[0-9]+(?:\.[0-9]+)?),\s*"
    r"Region:\s*(?P<region>[A-Z]+)\s*\]",
    re.IGNORECASE,
)

_DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
_NUMERIC_RE = re.compile(r"\b\d+\b")


def is_refusal(answer: str) -> bool:
    """True iff the answer is (essentially) the canonical refusal sentence."""
    return REFUSAL_STRING.strip().lower() in (answer or "").strip().lower()


def parse_citations(answer: str) -> list[dict]:
    return [m.groupdict() for m in _CITATION_RE.finditer(answer or "")]


# ---------------------------------------------------------------------------
# A1 — section reference present AND resolves to a real section
# ---------------------------------------------------------------------------
def assert_section_resolves(case: dict, answer: str):
    # Not applicable to answers that (correctly or not) refuse: there is no
    # citation to validate. Answerability itself is the judge's job, not this.
    if is_refusal(answer):
        return (False, None, "no citation in a refusal")

    cites = parse_citations(answer)
    if not cites:
        # A grounded answer with zero resolvable citations fails the check:
        # the app is instructed to cite every factual assertion.
        return (True, False, "grounded answer contains no parseable citation")

    bad = []
    for c in cites:
        policy = c["policy"].upper()
        region = c["region"].upper()
        section = c["section"]
        if policy not in VALID_POLICIES:
            bad.append(f"policy {policy} unknown")
        elif region not in VALID_REGIONS:
            bad.append(f"region {region} unknown")
        elif not section_exists(policy, region, section):
            bad.append(f"{policy}/{region} §{section} does not exist")
    if bad:
        return (True, False, "; ".join(bad))
    resolved = ", ".join(f"{c['policy']}/{c['region'].upper()}§{c['section']}" for c in cites)
    return (True, True, f"all citations resolve ({resolved})")


# ---------------------------------------------------------------------------
# A2 — handbook version (effective date) cited, and it is the CURRENT one
# ---------------------------------------------------------------------------
def assert_version_cited(case: dict, answer: str):
    expected = case.get("expected", {}).get("effective_date")
    policy = case.get("expected", {}).get("policy")
    region = case.get("expected", {}).get("region")
    if not expected:
        return (False, None, "case does not ask for a handbook version")

    dates = _DATE_RE.findall(answer or "")
    if not dates:
        return (True, False, "no handbook version / effective date cited in answer")
    if expected not in dates:
        return (True, False, f"cited {dates} but current version is {expected}")
    # Guard against a superseded date being cited alongside the right one.
    cur = current_version(policy, region) if policy and region else expected
    stale = [d for d in dates if d != cur]
    if stale:
        return (True, False, f"cites current {cur} but also superseded {stale}")
    return (True, True, f"cites current handbook version {expected}")


# ---------------------------------------------------------------------------
# A3 — notice / certification period is a NUMBER, not vague prose
# ---------------------------------------------------------------------------
def assert_notice_period_numeric(case: dict, answer: str):
    if not case.get("expected", {}).get("notice_numeric_required"):
        return (False, None, "case is not a notice/certification question")
    if is_refusal(answer):
        return (True, False, "refused a question that has a numeric notice window")
    if _NUMERIC_RE.search(answer or ""):
        nums = _NUMERIC_RE.findall(answer)
        return (True, True, f"numeric figure(s) present ({nums[:5]})")
    return (True, False, "no numeric day/week figure in a notice-window answer")


# ---------------------------------------------------------------------------
# A4 — out-of-jurisdiction / out-of-corpus triggers the refusal path
# ---------------------------------------------------------------------------
def assert_refusal_path(case: dict, answer: str):
    if not case.get("expected", {}).get("must_refuse"):
        return (False, None, "case is answerable, refusal not required")
    if is_refusal(answer):
        return (True, True, "correctly emitted the exact refusal string")
    return (True, False, "did NOT refuse an out-of-jurisdiction/out-of-corpus question")


ASSERTIONS = {
    "A1_section_resolves": assert_section_resolves,
    "A2_version_cited": assert_version_cited,
    "A3_notice_period_numeric": assert_notice_period_numeric,
    "A4_refusal_path": assert_refusal_path,
}

# The single criterion LEFT in the judge after the split (for reporting counts).
JUDGED_CRITERIA = ["policy_correctness"]


def run_assertions(case: dict, answer: str) -> dict:
    """Run every applicable assertion on one answer.

    Returns {name: {applicable, passed, detail}} plus an aggregate
    `assertions_passed` = True iff no applicable assertion failed.
    """
    results = {}
    agg = True
    for name, fn in ASSERTIONS.items():
        applicable, passed, detail = fn(case, answer)
        results[name] = {"applicable": applicable, "passed": passed, "detail": detail}
        if applicable and passed is False:
            agg = False
    results["_assertions_passed"] = agg
    return results
