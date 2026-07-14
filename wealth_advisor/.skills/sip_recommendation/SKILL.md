---
name: sip_recommendation
description: Propose a monthly SIP (Systematic Investment Plan) amount and fund mix based on the user's profile, existing goals, and SIP step-up guidance.
when_to_use: SIP recommendation, how much should I invest monthly, SIP step-up, increase my SIP
---

# SIP Recommendation

## Steps

1. Call `get_profile` for age, monthly income, risk tolerance, dependents. If
   any of these needed for a recommendation are missing, ask the user rather
   than guessing.
2. Call `get_goal_history` to see if the user already has a related goal
   (e.g. retirement, a target amount) — anchor the recommendation to an
   existing goal if one exists, instead of proposing one from scratch.
3. Call `retrieval_tool` for SIP step-up strategy and asset-allocation-by-age
   guidance from `retirement_and_sip_playbook.md`.
4. Propose: a monthly SIP amount (as a % of monthly income, respecting
   dependents/expenses), a fund-type mix (e.g. equity/debt split by risk
   tolerance), and a step-up schedule (e.g. increase X% annually).

## Output rules

- This is a proposal, not an executed action. Do **not** call any tool that
  saves this as a goal directly — tell the user to run `/set_goal <description>`
  with the specifics if they want this proposal saved, since that command
  already goes through the plan-approval flow (approve/modify/reject) before
  anything is persisted.
- Frame the step-up schedule and projected outcomes as illustrative, never
  as guaranteed returns.
- Always close with the disclaimer: this is educational information, not
  registered investment advice.
