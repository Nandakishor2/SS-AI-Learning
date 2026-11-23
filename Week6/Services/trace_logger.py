"""
Week 5 — Trace logging + PII redaction for the HR Leave Policy RAG assistant.

Every answered query is written to traces/traces.jsonl as ONE complete, replayable
trace: the question, the exact prompt version + model + params, the retrieved
chunk_ids WITH scores and text, and the raw model output.

Redaction requirement (Week 5 Task C, req. 1 + checklist):
    No employee names or IDs are written to the trace file unredacted.
    Redaction happens BEFORE write, not after, on both the question and the output.
"""
import re
import json
import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRACES_DIR = PROJECT_ROOT / "traces"
TRACES_FILE = TRACES_DIR / "traces.jsonl"

# App / prompt versioning — stored on every trace so a replay knows exactly
# which prompt+model+params produced the original output.
APP_VERSION = "hr-rag-week5-1.0"
PROMPT_VERSION = "hr-rag-sys-v1"

# ---------------------------------------------------------------------------
# Redaction — runs before anything touches disk.
# ---------------------------------------------------------------------------
# Order matters: emails before the generic ID catcher so we don't shred them.
_REDACTION_RULES = [
    # Emails
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[EMAIL_REDACTED]"),
    # Employee / staff IDs: E-4471, EMP-20233, EMP12345, Staff ID 88213, #4471
    (re.compile(r"\b(?:E|EMP|EMPL|STAFF|ID)[-\s]?\d{3,}\b", re.IGNORECASE), "[EMP_ID_REDACTED]"),
    (re.compile(r"#\d{3,}\b"), "[EMP_ID_REDACTED]"),
    # Phone numbers (loose)
    (re.compile(r"\+?\d[\d\s().-]{7,}\d"), "[PHONE_REDACTED]"),
    # Names introduced by a self-identifying phrase:
    #   "my name is Priya Menon", "this is Daniel O'Brien", "I am Jane Doe", "I'm Lee Wong,"
    # Only the trigger phrase is case-insensitive (scoped (?i:...)); the NAME itself
    # must be properly capitalized, so lowercase words like "off sick for" are not eaten.
    (re.compile(r"\b(?i:(my name is|this is|i am|i'm))\s+"
                r"([A-Z][A-Za-zÀ-ÿ'’]*(?:\s+[A-Z][A-Za-zÀ-ÿ'’.-]*){0,2})"),
                r"\1 [NAME_REDACTED]"),
]


def redact(text: str) -> str:
    """Strip employee-identifying material from free text before it is logged."""
    if not text:
        return text
    out = text
    for pattern, replacement in _REDACTION_RULES:
        out = pattern.sub(replacement, out)
    return out


def new_trace_id(index: int) -> str:
    return f"trc_{index:04d}"


def build_trace(*, trace_id, source, question, region_filter, retriever,
                model, temperature, top_k, prompt, contexts, raw_output):
    """Assemble one complete trace dict. Question + output are redacted here."""
    retrieved = [
        {
            "rank": c.get("rank"),
            "chunk_id": c.get("chunk_id"),
            "score": round(float(c.get("score", 0.0)), 6),
            "policy_id": c.get("policy_id"),
            "region": c.get("region"),
            "effective_date": c.get("effective_date"),
            "source_file": c.get("source_file"),
            "text": c.get("text", ""),
        }
        for c in contexts
    ]
    return {
        "trace_id": trace_id,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source": source,                      # "production" | "demo"
        "app_version": APP_VERSION,
        "prompt_version": PROMPT_VERSION,
        "model": model,
        "params": {
            "temperature": temperature,
            "top_k": top_k,
            "retriever": retriever,
        },
        "region_filter": region_filter,
        "question": redact(question),          # REDACTED before write
        "prompt": redact(prompt),              # full reconstructable prompt, redacted
        "retrieved": retrieved,                # chunk_ids + scores + text
        "raw_output": redact(raw_output),      # REDACTED before write
    }


def log_trace(trace: dict) -> None:
    TRACES_DIR.mkdir(parents=True, exist_ok=True)
    with open(TRACES_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(trace, ensure_ascii=False) + "\n")


def load_traces(source: str | None = None) -> list[dict]:
    if not TRACES_FILE.exists():
        return []
    traces = []
    with open(TRACES_FILE, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            t = json.loads(line)
            if source is None or t.get("source") == source:
                traces.append(t)
    return traces


def get_trace(trace_id: str) -> dict | None:
    for t in load_traces():
        if t.get("trace_id") == trace_id:
            return t
    return None
