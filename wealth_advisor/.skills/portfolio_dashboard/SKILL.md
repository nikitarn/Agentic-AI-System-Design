---
name: portfolio_dashboard
description: Render a formatted summary of the user's portfolio — holdings, allocation by type, and top gainers/losers — as a quick-glance dashboard.
when_to_use: dashboard, show my portfolio, portfolio summary, top gainers, top losers
---

# Portfolio Dashboard

## Steps

1. Call `get_portfolio`. If empty, tell the user to `/upload_portfolio <path>`
   first and stop.
2. Build a table with one row per holding: symbol, type, quantity, avg_price,
   current_price, market_value (quantity * current_price), and P&L
   (current_price - avg_price) * quantity.
3. Compute allocation % by type (stock vs mutual_fund) across the whole
   portfolio.
4. Sort holdings by P&L to identify the top 3 gainers and top 3 losers (fewer
   if the portfolio has fewer holdings).
5. Present, in this order:
   - The full holdings table
   - Allocation % by type
   - Top gainers / top losers

## Output rules

- This is a factual summary of held positions, not a recommendation — skip
  the disclaimer if the response contains no buy/sell/allocate suggestion.
- If the user asks a follow-up recommendation question after seeing the
  dashboard, use `portfolio_analysis` instead of extending this skill.
