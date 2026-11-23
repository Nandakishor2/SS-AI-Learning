"""
Week 6 — LLM-as-judge (single binary criterion: policy_correctness).

The judge prompt lives in a .txt file (judge_v1.txt / judge_v2.txt) so iterating
the judge is a prompt edit, diffable in git. The judge grades ONE answer and
returns {"verdict": PASS|FAIL, "reason": ...}. Verdicts are cached by
(judge_version, case_id, sha1(answer)) in eval/.judge_cache.json so re-runs and
offline runs are free and deterministic.

This module judges ONLY the subjective criterion. The deterministic criteria were
removed from the prompt and live in eval/assertions.py.
"""
import os
import re
import json
import time
import hashlib
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

JUDGE_MODEL = "gemini-2.5-flash"
JUDGE_TEMPERATURE = 0.0
CACHE_FILE = ROOT / "eval" / ".judge_cache.json"


def judge_prompt_path(version: str) -> Path:
    return ROOT / f"judge_{version}.txt"


def _context_str(answer_record: dict) -> str:
    blocks = []
    for c in answer_record.get("contexts", []):
        blocks.append(
            f"[Chunk {c['chunk_id']} | {c['policy_id']} | {c['region']} | "
            f"Effective {c.get('effective_date')}]\n{c['text']}"
        )
    return "\n\n---\n\n".join(blocks) if blocks else "(no context retrieved)"


def _fill(template: str, question: str, context: str, answer: str) -> str:
    # Explicit replace (NOT str.format) because the template contains literal
    # JSON braces that would break format().
    return (template
            .replace("{question}", question)
            .replace("{context}", context)
            .replace("{answer}", answer))


def _parse_verdict(text: str) -> tuple[str, str]:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group(0))
            v = str(obj.get("verdict", "")).strip().upper()
            if v in ("PASS", "FAIL"):
                return v, str(obj.get("reason", ""))[:300]
        except json.JSONDecodeError:
            pass
    up = text.upper()
    if "FAIL" in up and "PASS" not in up:
        return "FAIL", "(parsed from freeform)"
    if "PASS" in up and "FAIL" not in up:
        return "PASS", "(parsed from freeform)"
    return "ERROR", text[:300]


def _load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _save_cache(cache: dict) -> None:
    CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False))


def _cache_key(version: str, case_id: str, answer: str) -> str:
    h = hashlib.sha1(answer.encode("utf-8")).hexdigest()[:12]
    return f"{version}:{case_id}:{h}"


_CLIENT = None


def _client():
    global _CLIENT
    if _CLIENT is None:
        from google import genai
        _CLIENT = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    return _CLIENT


def judge_case(case: dict, answer_record: dict, version: str = "v1",
               cache: dict | None = None, use_cache: bool = True,
               offline: bool = False) -> dict:
    """Return {verdict, reason, cached}. offline=True forbids live calls."""
    answer = answer_record["answer"]
    key = _cache_key(version, case["case_id"], answer)
    own_cache = cache is None
    if cache is None:
        cache = _load_cache()

    if use_cache and key in cache:
        rec = dict(cache[key]); rec["cached"] = True
        return rec

    if offline:
        raise RuntimeError(
            f"offline judge run but no cached verdict for {case['case_id']} "
            f"({version}). Run once online to populate eval/.judge_cache.json.")

    template = judge_prompt_path(version).read_text()
    prompt = _fill(template, case["question"], _context_str(answer_record), answer)

    last_err = None
    for attempt in range(3):
        try:
            resp = _client().models.generate_content(
                model=JUDGE_MODEL, contents=prompt,
                config={"temperature": JUDGE_TEMPERATURE},
            )
            verdict, reason = _parse_verdict(resp.text or "")
            rec = {"verdict": verdict, "reason": reason}
            cache[key] = rec
            if own_cache:
                _save_cache(cache)
            out = dict(rec); out["cached"] = False
            return out
        except Exception as e:  # transient API errors
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"judge failed for {case['case_id']}: {last_err!r}")


def judge_all(cases: list[dict], answers: dict, version: str = "v1",
              offline: bool = False) -> dict:
    cache = _load_cache()
    out = {}
    for c in cases:
        out[c["case_id"]] = judge_case(
            c, answers[c["case_id"]], version=version,
            cache=cache, offline=offline)
    _save_cache(cache)
    return out
