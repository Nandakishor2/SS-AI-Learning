"""
The three tools, shared verbatim by the agent and the workflow.

DESCRIPTION CONTRACT (this is graded, and it is the real bug this week guards):
each tool names exactly ONE job and says what it is NOT, so the model never has to
guess between them. The three jobs are disjoint:

  get_employee_record   -> facts about ONE person   (no rules, no numbers table)
  get_jurisdiction_rules-> the NUMBERS for ONE place (enum; no person, no prose)
  search_handbook       -> the PROSE of a rule       (no person, no numbers table)

Sharpening these descriptions is how you kill tool thrash — NOT by bolting
"use the right tool" onto the system prompt (see common mistakes in the task).
"""
import json
from datetime import date
from pathlib import Path
from google.genai import types

_DATA = Path(__file__).resolve().parent / "data"
AS_OF = date(2026, 11, 16)  # tenure is measured as of this fixed date -> deterministic

JURISDICTIONS = ["APAC", "EMEA", "NA", "LATAM", "UK", "ANZ"]  # the enum, single source of truth

_employees = json.loads((_DATA / "employees.json").read_text())["employees"]
_rules = json.loads((_DATA / "jurisdiction_rules.json").read_text())["rules"]
_handbook = json.loads((_DATA / "handbook.json").read_text())["passages"]

# Running count of tool invocations, per tool name -> used by the race for "tool calls".
CALL_COUNTS = {"get_employee_record": 0, "get_jurisdiction_rules": 0, "search_handbook": 0}


def _tenure_months(hire_date: str) -> int:
    y, m, d = map(int, hire_date.split("-"))
    months = (AS_OF.year - y) * 12 + (AS_OF.month - m)
    if AS_OF.day < d:
        months -= 1
    return months


# --------------------------------------------------------------------------- tools
def get_employee_record(employee_id: str) -> dict:
    """Return ONE employee's HR facts: name, jurisdiction, tier, hire date, tenure."""
    CALL_COUNTS["get_employee_record"] += 1
    emp = _employees.get(employee_id)
    if not emp:
        return {"error": f"No employee with id {employee_id}"}
    return {
        "employee_id": employee_id,
        "name": emp["name"],
        "jurisdiction": emp["jurisdiction"],
        "tier": emp["tier"],
        "hire_date": emp["hire_date"],
        "tenure_months": _tenure_months(emp["hire_date"]),
        "caregiver_role": emp.get("caregiver_role"),
        "planned_absence_days": emp.get("planned_absence_days"),
    }


def get_jurisdiction_rules(jurisdiction: str) -> dict:
    """Return the structured leave NUMBERS for one jurisdiction (tenure/absence bands)."""
    CALL_COUNTS["get_jurisdiction_rules"] += 1
    rules = _rules.get(jurisdiction)
    if not rules:
        return {"error": f"Unknown jurisdiction {jurisdiction}. Use one of {JURISDICTIONS}."}
    return rules


def search_handbook(query: str, jurisdiction: str = None) -> list:
    """Return handbook PROSE passages matching a free-text query (keyword overlap)."""
    CALL_COUNTS["search_handbook"] += 1
    q = {w for w in query.lower().replace("?", " ").replace(",", " ").split() if len(w) > 2}
    scored = []
    for p in _handbook:
        if jurisdiction and p["jurisdiction"] != jurisdiction:
            continue
        hay = (p["title"] + " " + p["text"]).lower()
        overlap = sum(1 for w in q if w in hay)
        if overlap:
            scored.append((overlap, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {"policy_id": p["policy_id"], "jurisdiction": p["jurisdiction"], "section": p["section"],
         "title": p["title"], "text": p["text"]}
        for _, p in scored[:3]
    ]


DISPATCH = {
    "get_employee_record": lambda a: get_employee_record(a["employee_id"]),
    "get_jurisdiction_rules": lambda a: get_jurisdiction_rules(a["jurisdiction"]),
    "search_handbook": lambda a: search_handbook(a["query"], a.get("jurisdiction")),
}

# ---------------------------------------------- Gemini function declarations (schemas)
FUNCTION_DECLARATIONS = [
    types.FunctionDeclaration(
        name="get_employee_record",
        description=(
            "Look up ONE employee's HR record by employee_id. Returns that person's name, "
            "jurisdiction, tier, hire_date and computed tenure_months. Use this ONLY to fetch "
            "facts about a specific person. It does NOT contain any policy rule, number, or "
            "handbook text — for those use get_jurisdiction_rules or search_handbook."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"employee_id": types.Schema(type=types.Type.STRING,
                        description="Employee id, e.g. E002")},
            required=["employee_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_jurisdiction_rules",
        description=(
            "Return the structured NUMERIC leave parameters for ONE jurisdiction: the tenure "
            "bands (or absence bands) with the exact paid-weeks / cap-days / pay figures and the "
            "governing policy_id and section. Use this ONLY to get the numbers to compute an "
            "entitlement. It knows nothing about any individual employee, and returns data, not prose."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"jurisdiction": types.Schema(
                type=types.Type.STRING, enum=JURISDICTIONS,
                description="The employee's jurisdiction, exactly one of the enum values.")},
            required=["jurisdiction"],
        ),
    ),
    types.FunctionDeclaration(
        name="search_handbook",
        description=(
            "Search the free-text policy handbook and return matching PROSE passages (title + "
            "wording + section). Use this ONLY to find or quote the written wording of a rule — "
            "for example to cite the exact section. It does NOT look up employees and does NOT "
            "return the structured numbers table (use get_jurisdiction_rules for figures)."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "query": types.Schema(type=types.Type.STRING,
                         description="Free-text description of the rule to find."),
                "jurisdiction": types.Schema(type=types.Type.STRING, enum=JURISDICTIONS,
                         description="Optional jurisdiction filter."),
            },
            required=["query"],
        ),
    ),
]

GEMINI_TOOLS = [types.Tool(function_declarations=FUNCTION_DECLARATIONS)]


def reset_counts():
    for k in CALL_COUNTS:
        CALL_COUNTS[k] = 0
