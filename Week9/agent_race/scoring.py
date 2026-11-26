"""Deterministic pass/fail — no LLM judge in the pass gate, so the race's pass rate is
reproducible.

An expected token of the form "<number> <unit>" (e.g. "14 weeks", "3 days") passes if the
answer contains that number followed by that unit within the same clause, allowing filler
words in between ("3 unused annual-leave days" still matches "3 days"). Any other expected
token (e.g. "HR-208", "Fit Note") is matched as a plain case-insensitive substring."""
import re

_FIGURE = re.compile(r"^(\d+)\s+([a-z]+)$", re.I)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower().replace("-", " "))


def _has(answer_norm: str, expected: str) -> bool:
    m = _FIGURE.match(expected.strip())
    if m:
        num, unit = m.group(1), _norm(m.group(2))
        # number, then up to ~30 chars of filler, then the unit word
        return re.search(rf"\b{num}\b[\w\s]{{0,30}}?\b{unit}\b", answer_norm) is not None
    return _norm(expected) in answer_norm


def passed(answer: str, expected: list) -> bool:
    a = _norm(answer)
    return all(_has(a, e) for e in expected)
