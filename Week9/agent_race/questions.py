"""
The 10 employee questions the two systems race over.

Each references an employee by id (so the hard-coded workflow can parse it) but does
NOT state the jurisdiction or tenure — those must be discovered from the record, which
is exactly what forces the lookup-then-rules path.

`branching=True` marks a case where STEP 3 depends on what STEP 2 found: the answer
figure is chosen by the employee's tenure/probation band. 8 of the 10 branch; the task
asks for at least 3. `expected` are the substrings the final answer must contain to PASS
(deterministic scoring — no LLM judge in the pass gate).
"""

QUESTIONS = [
    {"id": "Q01", "employee_id": "E001", "branching": True,
     "question": "Employee E001 is taking primary-caregiver leave. How many weeks of fully paid leave are they entitled to?",
     "expected": ["8 weeks", "HR-208"]},
    {"id": "Q02", "employee_id": "E002", "branching": True,
     "question": "Employee E002 is taking primary-caregiver leave. How many weeks of fully paid leave are they entitled to?",
     "expected": ["14 weeks", "HR-208"]},
    {"id": "Q03", "employee_id": "E003", "branching": True,
     "question": "Employee E003 is taking primary-caregiver leave. How many weeks of fully paid leave are they entitled to?",
     "expected": ["18 weeks", "HR-208"]},
    {"id": "Q04", "employee_id": "E004", "branching": True,
     "question": "Employee E004 is taking primary-caregiver leave. How many weeks of fully paid leave are they entitled to?",
     "expected": ["6 weeks", "HR-208"]},
    {"id": "Q05", "employee_id": "E005", "branching": True,
     "question": "Employee E005 is taking primary-caregiver leave. How many weeks of fully paid leave are they entitled to?",
     "expected": ["12 weeks", "HR-208"]},
    {"id": "Q06", "employee_id": "E006", "branching": True,
     "question": "How many unused annual-leave days may employee E006 carry over into next year?",
     "expected": ["3 days", "HR-207"]},
    {"id": "Q07", "employee_id": "E007", "branching": True,
     "question": "How many unused annual-leave days may employee E007 carry over into next year?",
     "expected": ["10 days", "HR-207"]},
    {"id": "Q08", "employee_id": "E008", "branching": True,
     "question": "How many unused annual-leave days may employee E008 carry over into next year?",
     "expected": ["5 days", "HR-207"]},
    {"id": "Q09", "employee_id": "E009", "branching": False,
     "question": "Employee E009 will be on sick leave for 10 consecutive days. What certification is required and what is the pay treatment?",
     "expected": ["Fit Note", "HR-209"]},
    {"id": "Q10", "employee_id": "E010", "branching": True,
     "question": "How many fully paid personal-leave days is employee E010 entitled to this service year?",
     "expected": ["12 days", "HR-209"]},
]

# Shared, identical output contract for BOTH systems. Both must end with the figure and
# cite the policy id — the agent reaches it via a tool loop, the workflow via fixed steps.
SYSTEM_PROMPT = (
    "You are an HR entitlements assistant. Answer the employee's leave question using ONLY "
    "the data returned by the tools. The answer PATH depends on the employee: first find the "
    "employee's jurisdiction and tenure, then get that jurisdiction's rules, then select the "
    "band that matches the employee's tenure/probation/absence to compute the figure.\n"
    "OUTPUT CONTRACT: reply in 1-2 sentences, state the exact figure (e.g. '14 weeks', "
    "'3 days'), and cite the governing policy id (e.g. HR-208) and section. Do not invent numbers."
)
