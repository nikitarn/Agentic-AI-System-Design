from __future__ import annotations

from pydantic import BaseModel
from langchain.agents import create_agent

from financial_analyst.llm.factory import get_llm
from financial_analyst.observability.logger import get_logger

logger = get_logger(__name__)


class PlanStep(BaseModel):
    id: str  # stable snake_case e.g. step_001
    action: str  # e.g. "increase_sip", "rebalance", "tax_harvest"
    description: str
    target_month: int  # months from now
    depends_on: list[str]  # step IDs that must happen first


class GoalPlan(BaseModel):
    goal_summary: str
    target_type: str  # growth_pct / retirement / target_amount
    target_value: float
    horizon_months: int
    steps: list[PlanStep]
    assumptions: list[str]
    risks: list[str]


_SYSTEM_PROMPT = """\
You are a financial planning assistant for Indian retail investors. Given a
financial goal, produce a structured GoalPlan broken into concrete steps.

Rules:
- 3 to 8 steps
- Step IDs must be stable snake_case: step_001, step_002, ...
- depends_on must reference valid step IDs in the same plan
- target_month is months from now when that step should happen
- Never state returns as guaranteed — describe them as probabilistic/illustrative
- This is educational information, not registered investment advice
"""


def create_plan(goal: str, extra_context: str = "") -> GoalPlan:
    """Call the LLM planner and return a structured GoalPlan."""
    llm = get_llm()

    planner_agent = create_agent(
        llm,
        tools=[],
        system_prompt=_SYSTEM_PROMPT,
        response_format=GoalPlan,
    )

    user_message = f"Goal: {goal}"
    if extra_context:
        user_message += f"\n\nAdditional context / change requests:\n{extra_context}"

    result = planner_agent.invoke({"messages": [{"role": "user", "content": user_message}]})
    plan: GoalPlan = result["structured_response"]
    logger.info(f"Plan created: {plan.goal_summary} with {len(plan.steps)} steps")
    return plan
