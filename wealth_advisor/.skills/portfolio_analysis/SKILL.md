---
name: portfolio_analysis
description: Analyze the user's current portfolio — allocation by asset type, concentration risk, and unrealized P&L per holding — and compare it against a suitable target allocation.
when_to_use: portfolio analysis, asset allocation, concentration risk, P&L, am I diversified, is my portfolio balanced
---

# Portfolio Analysis

## Steps

1. Call `get_portfolio` to fetch the user's holdings. If empty, tell the user
   to `/upload_portfolio <path>` first and stop.
2. Call `get_profile` to fetch age, risk tolerance, and dependents. If missing,
   ask the user for risk tolerance before proposing a target allocation — don't
   guess it.
3. Compute, from the holdings:
   - Allocation % by type (stock vs mutual_fund) — market_value = quantity * current_price
   - Unrealized P&L per holding — (current_price - avg_price) * quantity
   - Concentration risk — flag any single holding above ~25% of total market value
4. Call `retrieval_tool` for target-allocation guidance from
   `retirement_and_sip_playbook.md` (asset allocation by age bracket / risk
   tolerance), and compare the user's actual allocation against it.
5. Summarize: current allocation, top P&L gainers/losers, any concentration
   flags, and how far the current allocation is from the suggested target —
   in percentage-point terms, not as a directive to trade.

## Output rules

- State allocation drift as an observation ("you're 15pp overweight equity vs.
  the typical target for your risk profile"), not as an instruction to act.
- Never state that rebalancing will produce a specific return.
- Always close with the disclaimer: this is educational information, not
  registered investment advice.
