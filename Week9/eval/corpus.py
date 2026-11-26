"""
Week 6 — Policy corpus registry (the deterministic ground truth).

This is the lookup table the deterministic assertions use. It is built ONCE from
the handbook addenda (the same 6 PDFs ingested into Qdrant) so that checks like
"does this section reference resolve to a real section?" and "is the correct
handbook version cited?" are answered by an `if` + a dict lookup — never by a
paid model call. (See Week 6 common-mistake: *"Paying a model to check whether a
section reference resolves ... `if` and a lookup table do that for free."*)
"""

# Valid policy identifiers and jurisdictions in the corpus.
VALID_POLICIES = {"HR-207", "HR-208", "HR-209"}
VALID_REGIONS = {"APAC", "EMEA", "LATAM", "NA", "ANZ", "UK"}

# The exact section numbers that EXIST in each (policy, region) addendum.
# A section reference resolves iff (policy, region, section) is in this registry.
SECTION_REGISTRY = {
    ("HR-207", "APAC"): {"1", "2", "3", "3.1", "3.2"},
    ("HR-207", "EMEA"): {"1", "2", "3", "3.1", "3.2"},
    ("HR-208", "LATAM"): {"1", "2", "2.1", "2.2"},
    ("HR-208", "NA"): {"1", "2", "2.1", "2.2"},
    ("HR-209", "ANZ"): {"1", "2", "2.1", "2.2"},
    ("HR-209", "UK"): {"1", "2", "2.1", "2.2"},
}

# The authoritative "handbook version" of each addendum == its effective date.
# An answer that cites a handbook version must cite the CURRENT one for that
# (policy, region). Superseded dates (see ragas_bonus.py) are faithfully-wrong.
HANDBOOK_VERSION = {
    ("HR-207", "APAC"): "2026-01-01",
    ("HR-207", "EMEA"): "2026-02-01",
    ("HR-208", "LATAM"): "2026-03-01",
    ("HR-208", "NA"): "2026-01-15",
    ("HR-209", "ANZ"): "2026-04-01",
    ("HR-209", "UK"): "2026-01-01",
}

# The exact refusal sentence the app is instructed to emit (rag_engine
# SYSTEM_INSTRUCTION rule 2). The refusal-path assertion matches on this.
REFUSAL_STRING = (
    "I do not have sufficient information in the provided leave policy "
    "documents to answer this question."
)


def section_exists(policy: str, region: str, section: str) -> bool:
    return section in SECTION_REGISTRY.get((policy, region), set())


def current_version(policy: str, region: str) -> str | None:
    return HANDBOOK_VERSION.get((policy, region))
