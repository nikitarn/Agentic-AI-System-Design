# Retirement Planning & SIP Playbook

> Educational reference content, not registered investment advice. All
> formulas below are rules of thumb, not precise projections — actual
> results depend on real returns, inflation, and life events that no
> formula captures.

## SIP Step-Up Strategy

A **Step-Up SIP** (also called a "top-up SIP") increases the monthly
investment amount by a fixed percentage every year, instead of holding it
flat — typically aligned with expected salary growth.

- **Typical step-up rate**: 10–15% per year is the commonly cited range.
- **Why it matters**: because contributions grow alongside income (rather
  than staying fixed while inflation erodes their real value), a step-up
  SIP can produce **40–50% more terminal wealth** than a flat SIP of the
  same starting amount over a long horizon.
- **Worked illustration** (illustrative, not a guarantee): starting at
  ₹10,000/month (10% of a ₹1 lakh income), stepped up 10% annually, invested
  in an equity fund assumed to compound at 10% p.a. for 25 years, arrives at
  a corpus in the ballpark of ₹4+ crore. The exact figure is highly
  sensitive to the assumed return — always caveat any such number as
  assumption-dependent, never present it as promised.
- **Late-start options** when a user has limited runway: maximize EPF
  voluntary contribution (VPF), max out the ₹1.5 lakh/year PPF limit, and
  use a more aggressive step-up rate (15%+) on the equity SIP to compensate
  for lost time.

## Retirement Corpus — Rules of Thumb

Two commonly used estimation approaches, useful for a first-pass answer
before pointing the user to a proper calculator or advisor:

1. **The 25x Rule (a version of the 4% withdrawal rule)** — target a corpus
   equal to **25–30x your expected first-year retirement expenses**. Comes
   from assuming a **4% safe withdrawal rate**: withdrawing 4% of the corpus
   in year one, then adjusting that withdrawal for inflation each
   subsequent year, is intended to make the corpus last 30+ years.
   - Formula: `corpus_needed = annual_expenses_at_retirement / 0.04`
   - Example: ₹50,000/month expenses today, 25 years to retirement, 6%
     inflation → ~₹2.15 lakh/month (~₹25.7 lakh/year) at retirement →
     corpus needed ≈ ₹25.7 lakh / 0.04 ≈ **₹6.4 crore**.
2. **The 10% savings rule** — as a simpler input-side heuristic, saving
   ~10% of gross income annually into a retirement-directed SIP, escalated
   over a multi-decade career, is often cited as a baseline starting point
   — though the 25x/4%-rule above is the better *output-side* sanity check
   for whether that 10% is actually enough for a specific user's expense
   level.

Both rules are **planning heuristics, not precise formulas** — actual
requirement depends on post-retirement inflation, life expectancy,
healthcare costs, and the real (inflation-adjusted) return the corpus earns
after retirement. Always frame outputs as "a reasonable starting estimate,"
never as "you will need exactly X."

## Asset Allocation by Age

The **100-minus-age rule** (and its more aggressive Indian-market variant,
**110-minus-age**) is a starting heuristic for how much of a portfolio
should sit in equity vs. debt/other:

- `equity_% = 100 - age` (conservative) or `110 - age` (more aggressive,
  often cited as better suited to India's higher long-run growth trajectory
  and younger investors' longer earning horizon)
- Remainder goes to debt, gold, or other lower-volatility assets.

| Age Bracket | Equity % (100-age) | Equity % (110-age, aggressive) | Rationale |
|-------------|---------------------|-----------------------------------|-----------|
| 25–35        | 65–75%               | 75–85%                             | Long horizon, high risk capacity, time to recover from drawdowns |
| 36–45        | 55–65%               | 65–75%                             | Still growth-oriented but starting to de-risk |
| 46–55        | 45–55%               | 55–65%                             | Balancing growth with capital protection as retirement nears |
| 56–65        | 35–45%               | 45–55%                             | Near-retirement, prioritize stability and income |
| 65+          | ≤35%                 | ≤45%                                | Capital preservation, income generation in retirement |

This is the lookup table `analysis/rebalance.py`'s `target_allocation()`
should mirror in code (as a small hardcoded table, LLM-free) — keep the two
in sync if either changes.

**Important caveat**: this rule ignores individual risk tolerance,
dependents, existing liabilities, and specific goals — it's a starting
framework to be adjusted per user profile (`profile_store.py`'s
`risk_tolerance` field), not a rigid formula to apply uniformly.
