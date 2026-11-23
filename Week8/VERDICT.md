# Verdict

**Ship the workflow for this question set.**

| metric | agent | workflow |
|---|---|---|
| pass rate | 100% | 100% |
| p50 latency | 4404 ms | **1740 ms** |
| total tokens (10 q) | 24,792 | **6,244** |
| cost / question | $0.001630 | **$0.000695** |

Decision rule: *does the answer path vary by input?* It varies in **value** — 8 of 10
cases branch on tenure/probation — but not in **shape**. Every question is the same fixed
three steps: look up the employee, fetch that jurisdiction's rules, pick the band. A
hard-coded `if` resolves the branch for free; the agent re-sends the whole message list
each lap and pays ~2.3× the cost and ~2.5× the latency to rediscover an order we already
know. Same pass rate, so adaptability bought nothing here.

**None of the 10 forces an agent.** The class that would: *open-ended multi-hop* — where
the number of lookups isn't known until intermediate results are read (e.g. "compare this
employee's entitlement against every jurisdiction they've worked in"). There the step
count is data-dependent, and only then does the loop earn its cost.

*(148 words)*
