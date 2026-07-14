---
name: tax_planning
description: Review the user's ELSS/80C usage from their portfolio and suggest tax-saving instruments based on Indian tax rules.
when_to_use: tax planning, Section 80C, ELSS, tax saving, how much tax can I save
---

# Tax Planning

## Steps

1. Call `get_portfolio` to check existing ELSS (tax-saving mutual fund)
   holdings and estimate current Section 80C utilization.
2. Call `get_profile` for monthly income (needed to estimate tax bracket and
   80C headroom). If missing, ask the user rather than guessing.
3. Call `retrieval_tool` for the relevant rules from `tax_rules_india.md`
   (Section 80C limit, ELSS lock-in period, LTCG/STCG treatment) — cite the
   specific rule you're applying.
4. Suggest tax-saving instruments/amounts that fit within remaining 80C
   headroom, referencing the ELSS lock-in and any relevant capital-gains
   treatment.

## Output rules

- Must include this disclaimer **verbatim**, exactly once, at the end of the
  response: "This is educational information, not tax advice — consult a
  qualified CA for your specific tax situation."
- Never state a specific tax saving amount as certain — tax outcomes depend
  on the user's full income and deductions, which this tool doesn't have
  complete visibility into.
