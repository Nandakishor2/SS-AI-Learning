"""
Week 8 · scoring ONE captured trajectory against its expected path.

This is the heart of the trajectory eval: given the ordered tool calls the agent actually
made for a question, decide
  • tool-choice: did it follow an accepted path (right tools, record first)?       [req 2]
  • argument validity: were the ids/jurisdictions real, or fluent fiction?          [req 2]
  • step efficiency: steps taken / steps needed.                                    [req 2]
  • trajectory_pass: all of the above clean AND it stopped on an answer (not a budget).
  • failure mode: which entry in the Week-8 zoo this trajectory fell into.          [req 4/5]

Outcome pass (did the final figure match) is scored elsewhere by agent_race.scoring; the
GAP between the two is the whole point (req 3).
"""
from agent_race.tools import JURISDICTIONS
from trajectory.expected import EXPECTED, REC, RULES, BOOK, sequence_is_valid

NUMBER_TOOLS = (RULES, BOOK)           # tools that produce the figure
VALID_EMPLOYEE_IDS = set(EXPECTED[q]["employee_id"] for q in EXPECTED)


def _executed(record):
    """Tool calls that actually ran (a blocked call did not execute)."""
    return [c for c in record["trajectory"] if not c.get("blocked")]


def arg_checks(record):
    """One (call_name, valid, reason) per EXECUTED call — 'valid' = a real argument, not
    fluent fiction. employee_id must be a real id; jurisdiction a real enum value that
    matches the employee's actual jurisdiction."""
    gt = EXPECTED[record["qid"]]
    out = []
    for c in _executed(record):
        name, a = c["name"], c.get("args", {})
        if name == REC:
            eid = a.get("employee_id")
            ok = eid in VALID_EMPLOYEE_IDS and eid == gt["employee_id"]
            out.append((name, ok, "real id" if ok else f"bad id {eid!r}"))
        elif name == RULES:
            j = a.get("jurisdiction")
            ok = j in JURISDICTIONS and j == gt["jurisdiction"]
            out.append((name, ok, "real jurisdiction" if ok else f"fiction/wrong {j!r}"))
        elif name == BOOK:
            j = a.get("jurisdiction")
            ok = (j is None) or (j in JURISDICTIONS and j == gt["jurisdiction"])
            out.append((name, ok, "ok" if ok else f"bad jurisdiction {j!r}"))
        else:
            # the fast-path tool: leave_type is a real enum value, so the ARG is well-formed
            # (the failure here is tool-choice, not fiction — kept honest and separate).
            out.append((name, True, "well-formed arg"))
    return out


def analyze(record):
    """Return the full per-question trajectory verdict."""
    gt = EXPECTED[record["qid"]]
    executed = _executed(record)
    name_seq = [c["name"] for c in executed]
    attempts = len(record["trajectory"])            # incl. blocked -> the work actually spent
    steps_needed = gt["steps_needed"]

    read_record = REC in name_seq
    got_numbers = any(n in NUMBER_TOOLS for n in name_seq)
    # order: index of the record vs first numbers tool
    first_num = next((i for i, n in enumerate(name_seq) if n in NUMBER_TOOLS), None)
    rec_idx = name_seq.index(REC) if read_record else None
    record_before_numbers = read_record and (first_num is None or rec_idx < first_num)

    checks = arg_checks(record)
    args_all_valid = all(ok for _, ok, _ in checks)
    seq_valid = sequence_is_valid(record["qid"], name_seq)
    answered = record["stop_reason"] == "answered"

    trajectory_pass = seq_valid and args_all_valid and answered

    mode = _classify(record, name_seq, read_record, got_numbers, record_before_numbers,
                     args_all_valid, seq_valid, answered, attempts, steps_needed)

    return {
        "qid": record["qid"],
        "name_seq": name_seq,
        "read_record": read_record,
        "record_before_numbers": record_before_numbers,
        "args_valid": args_all_valid,
        "arg_checks": checks,
        "seq_valid": seq_valid,
        "answered": answered,
        "trajectory_pass": trajectory_pass,
        "outcome_pass": record["outcome_pass"],
        "steps_taken": attempts,
        "steps_needed": steps_needed,
        "step_efficiency": attempts / steps_needed if steps_needed else float("nan"),
        "mode": mode,
        "right_answer_wrong_path": record["outcome_pass"] and not trajectory_pass,
    }


def _classify(record, name_seq, read_record, got_numbers, record_before_numbers,
              args_all_valid, seq_valid, answered, attempts, steps_needed):
    """The Week-8 failure zoo (one label per trajectory)."""
    if not answered:                                    # hit a budget / spun
        return "budget_terminated"
    if not read_record:                                 # never looked the person up
        return "skipped_lookup"
    if not record_before_numbers:                       # fetched numbers before the record
        return "wrong_tool_order"
    if not args_all_valid:                              # real person, but a fiction argument
        return "guessed_jurisdiction"
    if not seq_valid:                                   # right tools, but an odd shape
        return "off_path"
    if attempts >= 2 * steps_needed:                    # clean path but wandered/thrashed
        return "redundant_steps"
    return "clean"


# The full zoo, for the regression table to list every mode it checked (req 5).
ALL_MODES = ["clean", "skipped_lookup", "wrong_tool_order", "guessed_jurisdiction",
             "off_path", "redundant_steps", "budget_terminated"]
