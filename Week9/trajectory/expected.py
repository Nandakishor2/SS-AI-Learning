"""
Week 8 · the EXPECTED tool trajectory for each of the 10 HR cases (Requirement 1).

A trajectory eval scores the PATH, not just the answer. To do that we must state, up
front and in code, what a correct path looks like for each question — and, crucially,
accept the cases that have MORE THAN ONE legitimate path as a SET of sequences rather
than over-asserting a single one (the task calls brittle single-sequence asserts a
common mistake).

The task for every one of these 10 questions has the same correct SHAPE:

    1. get_employee_record(<the id in the question>)   # discover jurisdiction + tenure
    2. get the NUMBERS for that jurisdiction            # compute the figure
       └─ get_jurisdiction_rules(<that jurisdiction>)   # the structured table, OR
       └─ search_handbook(..., <that jurisdiction>)     # the prose carries the figure too

The ONE rule that must hold: the employee record is read FIRST. The whole failure this
week hunts is answering the entitlement WITHOUT reading the person — guessing the
jurisdiction/tenure and getting lucky. So any sequence that reaches the numbers before
(or without) the record is a trajectory FAIL even if the final figure is right.

`multi_path=True` marks the cases that legitimately accept more than one ordering —
here, reading the handbook before OR after the rules, or citing from the handbook
instead of the rules table. Those are accepted as a set, not scored as failures.
"""

# Ground-truth jurisdiction per employee (from agent_race/data/employees.json) — the
# value a correct get_jurisdiction_rules / search_handbook call MUST carry.
EMP_JURISDICTION = {
    "E001": "NA",  "E002": "NA",    "E003": "NA",
    "E004": "LATAM", "E005": "LATAM",
    "E006": "APAC", "E007": "APAC",
    "E008": "EMEA",
    "E009": "UK",
    "E010": "ANZ",
}

REC = "get_employee_record"
RULES = "get_jurisdiction_rules"
BOOK = "search_handbook"


def _valid_sequences():
    """The acceptable tool-NAME sequences for every entitlement case (identical shape).

    Accepted as a SET (multi-path): record first, then the numbers from the rules table
    and/or the handbook prose, in either order. Rejected: anything that does not start
    with the record, or that never fetches the numbers after it.
    """
    return [
        [REC, RULES],                 # canonical minimal path (2 steps)
        [REC, RULES, BOOK],           # + cite the prose/section (fine, 1 extra step)
        [REC, BOOK, RULES],           # read the prose first, then confirm the table
        [REC, BOOK],                  # the handbook passage carries both figure and section
    ]


# case_id -> ground truth. steps_needed is the MINIMAL correct tool count (record+numbers).
EXPECTED = {}
for _qid, _eid in [
    ("Q01", "E001"), ("Q02", "E002"), ("Q03", "E003"), ("Q04", "E004"), ("Q05", "E005"),
    ("Q06", "E006"), ("Q07", "E007"), ("Q08", "E008"), ("Q09", "E009"), ("Q10", "E010"),
]:
    EXPECTED[_qid] = {
        "employee_id": _eid,
        "jurisdiction": EMP_JURISDICTION[_eid],
        "valid_sequences": _valid_sequences(),
        "steps_needed": 2,
        "multi_path": True,   # every case accepts the handbook-before/after/instead variants
        "must_start_with": REC,
    }


def sequence_is_valid(qid: str, name_seq: list) -> bool:
    """True iff the actual tool-name sequence matches one accepted path for this case."""
    return name_seq in EXPECTED[qid]["valid_sequences"]
