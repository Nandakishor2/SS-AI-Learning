# Third tool — description diff & parameter enums

The loop already had two tools. Adding a third is where overlap creeps in, so the diff
below does two things at once: (1) adds `get_jurisdiction_rules` with **one job** and a
**typed enum**, and (2) sharpens the two existing descriptions so all three jobs are
disjoint. Fixing tool thrash by sharpening descriptions — not by adding
"use the right tool" to the system prompt — is the point of this week.

All three live in [`agent_race/tools.py`](agent_race/tools.py).

## The three jobs, made disjoint

| tool | the ONE job | explicitly NOT |
|---|---|---|
| `get_employee_record` | facts about **one person** | no rules, no numbers, no prose |
| `get_jurisdiction_rules` | the **numbers** for one place (enum) | no person, no prose |
| `search_handbook` | the **prose** of a rule | no person, no numbers table |

## Diff

```diff
+ # ───────────────── ADDED: the third tool ─────────────────
+ get_jurisdiction_rules(jurisdiction: enum["APAC","EMEA","NA","LATAM","UK","ANZ"])
+   """Return the structured NUMERIC leave parameters for ONE jurisdiction: the tenure
+   bands (or absence bands) with the exact paid-weeks / cap-days / pay figures and the
+   governing policy_id and section. Use this ONLY to get the numbers to compute an
+   entitlement. It knows nothing about any individual employee, and returns data, not prose."""
+   # parameter `jurisdiction` is a STRING with enum=JURISDICTIONS (6 values) — not free text.

  # ───────────────── SHARPENED: existing tool #1 ─────────────────
  get_employee_record(employee_id: str)
-   "Get an employee's details."                      # old: vague; overlaps 'details' with rules
+   """Look up ONE employee's HR record by employee_id. Returns that person's name,
+   jurisdiction, tier, hire_date and computed tenure_months. Use this ONLY to fetch
+   facts about a specific person. It does NOT contain any policy rule, number, or
+   handbook text — for those use get_jurisdiction_rules or search_handbook."""

  # ───────────────── SHARPENED: existing tool #2 ─────────────────
  search_handbook(query: str, jurisdiction: enum = optional)
-   "Search the HR handbook for policy information."  # old: 'policy information' overlaps the
-                                                      #      numbers tool AND the record tool
+   """Search the free-text policy handbook and return matching PROSE passages (title +
+   wording + section). Use this ONLY to find or quote the written wording of a rule — for
+   example to cite the exact section. It does NOT look up employees and does NOT return the
+   structured numbers table (use get_jurisdiction_rules for figures)."""
```

## Why the enum matters

`jurisdiction` is declared `types.Schema(type=STRING, enum=["APAC","EMEA","NA","LATAM","UK","ANZ"])`.
The model cannot pass `"North America"` or `"apac-region"`; it must emit one of six legal
values, which are the exact keys of the rules table — so the lookup can never miss on a
spelling. The enum is defined once (`tools.JURISDICTIONS`) and reused by both the record
data and the two tool schemas, so there is a single source of truth.

## Overlap check (what each description forbids)

- `get_employee_record` **forbids** rules/numbers/prose → cannot be confused with the other two.
- `get_jurisdiction_rules` **forbids** person/prose → cannot be confused with record or handbook.
- `search_handbook` **forbids** person/numbers-table → cannot be confused with record or rules.

No pair shares a job, so the model never has to guess which tool owns "policy information".
