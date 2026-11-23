"""
Week 8 · the agent configurations the trajectory eval compares.

WHY A SEEDED REGRESSION, HONESTLY STATED
----------------------------------------
The vanilla Week-7 agent (sharp tool descriptions, enum jurisdiction, strong prompt) is
already clean: probing it — even after re-introducing vague descriptions and a free-text
jurisdiction — shows it ALWAYS reads the employee record first and passes a legal
jurisdiction code. Gemini 2.5 Flash at temp 0 is robust to prompt/description quality on
this task, so tool-description quality alone will not move the trajectory. A trajectory
eval you cannot trip teaches nothing (the Week-6 lesson: validate the instrument).

So we study the real, common production regression the task is about: a prior engineer,
optimising for latency and cost, adds a `get_quick_entitlement` FAST PATH that returns the
STANDARD (modal) figure without a per-employee lookup, and prompts the agent to prefer the
fewest calls. That one addition makes the agent answer every question WITHOUT reading the
employee — right by luck on the modal-tenure employees (E001, E007), wrong on the other 8.
That is exactly the brief's bug: "the right figure without ever reading the tenure."

  v0_control   — the hardened Week-7 agent, no fast path. The clean reference (gap 0).
  v1_baseline  — hardened tools + the fast-path tool + a latency prompt. The regression.
  v2_mitigated — v1 + EXACTLY ONE change: a record-first argument-validation GUARD that
                 refuses any entitlement not grounded in a get_employee_record lookup.

Model, temperature, questions and scoring are identical across all three, so any change
in the trajectory numbers is attributable to the one change between v1 and v2.
"""
from google.genai import types
from agent_race import tools

# --------------------------------------------------------------- the fast-path tool
# The STANDARD (modal) figure per leave type — no employee lookup. Correct ONLY for the
# modal-tenure employee of each class, which is precisely why it passes "by luck".
_STANDARD = {
    "primary_caregiver":  {"standard_answer": "8 weeks fully paid", "policy_id": "HR-208",
                           "basis": "standard entry-level figure"},
    "carryover":          {"standard_answer": "10 days", "policy_id": "HR-207",
                           "basis": "standard confirmed-employee cap"},
    "sick_certification": {"standard_answer": "Self-certification, 100% salary", "policy_id": "HR-209",
                           "basis": "standard short-absence rule"},
    "personal_leave":     {"standard_answer": "10 days", "policy_id": "HR-209",
                           "basis": "standard Year-1 figure"},
}
_LEAVE_TYPES = list(_STANDARD)


def get_quick_entitlement(args: dict) -> dict:
    return _STANDARD.get(args.get("leave_type"), {"error": "unknown leave_type"})


# dispatch used by the two fast-path variants (the three real tools + the shortcut)
FAST_DISPATCH = dict(tools.DISPATCH)
FAST_DISPATCH["get_quick_entitlement"] = get_quick_entitlement

_FAST_DECL = types.FunctionDeclaration(
    name="get_quick_entitlement",
    description=("Fast path: return the STANDARD entitlement figure for a leave type directly, "
                "without a per-employee record lookup. Prefer this for a quick answer."),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={"leave_type": types.Schema(type=types.Type.STRING, enum=_LEAVE_TYPES)},
        required=["leave_type"],
    ),
)
FAST_TOOLS = [types.Tool(function_declarations=list(tools.FUNCTION_DECLARATIONS) + [_FAST_DECL])]

FAST_PROMPT = (
    "You are a FAST HR entitlements assistant optimized for low latency and cost. "
    "For any leave-entitlement question, call get_quick_entitlement with the matching "
    "leave_type and answer directly from it — this is the approved fast path. Do NOT look up "
    "individual employee records unless the fast path returns an error. Reply in 1-2 sentences "
    "with the figure and the governing policy id (e.g. HR-208)."
)
# NOTE: this prompt encodes a REAL misconfiguration — a latency-focused engineer wiring the
# agent to trust a cache over the per-employee record. It is deterministic on purpose, so the
# regression (and therefore the whole eval) reproduces. The FIX is deliberately NOT "revert
# the prompt": a prompt is not an enforcement boundary (it can be re-broken, or injected around
# — see trajectory/injection.py). The mitigation is the record-first GUARD, a mechanism the
# model cannot talk its way past.


# ------------------------------------------------------------------- the mitigation
def record_first_guard(name: str, args: dict, revealed: dict):
    """ARGUMENT / PRECONDITION VALIDATION (the one mitigation).

    An entitlement must be grounded in the employee's own record. This guard refuses the
    fast path outright, and refuses rules/handbook calls whose jurisdiction was never
    obtained from a get_employee_record this run. Returns a corrective error the model
    reads and re-plans from — it does NOT touch the system prompt (patching the prompt is
    the common mistake the task warns against). Returns None to allow the call.
    """
    if name == "get_quick_entitlement":
        return {"error": "BLOCKED: the fast path cannot read the employee's tenure or "
                "jurisdiction, so it must not be used for an entitlement answer. Call "
                "get_employee_record(employee_id) first, then get_jurisdiction_rules(jurisdiction)."}
    if name in ("get_jurisdiction_rules", "search_handbook") and not revealed.get("jurisdiction"):
        return {"error": "BLOCKED: call get_employee_record first to obtain the employee's "
                "jurisdiction; do not supply a jurisdiction you have not looked up."}
    return None


# --------------------------------------------------------------------- the variants
VARIANTS = {
    "v0_control": {
        "label": "hardened Week-7 agent (no fast path) — clean reference",
        "system_prompt": None, "gemini_tools": tools.GEMINI_TOOLS,
        "dispatch": tools.DISPATCH, "guard": None,
    },
    "v1_baseline": {
        "label": "fast-path regression (latency prompt + get_quick_entitlement)",
        "system_prompt": FAST_PROMPT, "gemini_tools": FAST_TOOLS,
        "dispatch": FAST_DISPATCH, "guard": None,
    },
    "v2_mitigated": {
        "label": "v1 + record-first guard (one change)",
        "system_prompt": FAST_PROMPT, "gemini_tools": FAST_TOOLS,
        "dispatch": FAST_DISPATCH, "guard": record_first_guard,
    },
}
