from langchain.tools import tool

from financial_analyst.memory import profile_store, portfolio_store, goal_store
from financial_analyst.observability.logger import get_logger

logger = get_logger(__name__)


def build_memory_tools(user_id: str) -> list:
    """Build the long-term-memory lookup tools, bound to a single user_id."""

    @tool
    def get_profile() -> str:
        """Look up the user's saved financial profile: age, monthly income,
        risk tolerance, dependents. Use before giving personalized advice."""
        logger.info(f"Tool called: get_profile ({user_id})")
        profile = profile_store.get_profile(user_id)
        return str(profile) if profile else "No profile saved yet for this user."

    @tool
    def get_portfolio() -> str:
        """Look up the user's saved portfolio holdings (stocks, mutual funds)."""
        logger.info(f"Tool called: get_portfolio ({user_id})")
        holdings = portfolio_store.get_portfolio(user_id)
        if not holdings:
            return "No portfolio saved yet for this user."
        return "\n".join(
            f"{h['symbol']} ({h['type']}): qty={h['quantity']}, "
            f"avg_price={h['avg_price']}, current_price={h['current_price']}"
            for h in holdings
        )

    @tool
    def get_transactions() -> str:
        """Look up the user's saved bank statement transactions."""
        logger.info(f"Tool called: get_transactions ({user_id})")
        rows = portfolio_store.get_transactions(user_id)
        if not rows:
            return "No transactions saved yet for this user."
        return "\n".join(
            f"{r['date']}: {r['description']} "
            f"(debit={r['debit']}, credit={r['credit']}, balance={r['balance']})"
            for r in rows
        )

    @tool
    def get_goal_history() -> str:
        """Look up the user's past financial goals and their approved plans."""
        logger.info(f"Tool called: get_goal_history ({user_id})")
        goals = goal_store.get_goal_history(user_id)
        if not goals:
            return "No goals saved yet for this user."
        return "\n".join(
            f"{g['description']} (target: {g['target_type']}={g['target_value']}, "
            f"{g['horizon_months']}mo, approved={g['plan_approved']})"
            for g in goals
        )

    return [get_profile, get_portfolio, get_transactions, get_goal_history]


def build_goal_tools(user_id: str) -> list:
    """Side-effecting tool(s) — gated behind HumanInTheLoopMiddleware in
    agent/factory.py, since this persists to long-term memory."""

    @tool
    def propose_goal(description: str, target_type: str, target_value: float, horizon_months: int) -> str:
        """Save a financial goal for the user. target_type is one of
        growth_pct / retirement / target_amount. Only call this after the
        user has confirmed, in this conversation, that they want this exact
        goal saved — this action requires human approval before it persists."""
        logger.info(f"Tool called: propose_goal ({user_id}): {description}")
        goal_id = goal_store.save_goal(user_id, description, target_type, target_value, horizon_months)
        return f"Goal saved (id: {goal_id})."

    return [propose_goal]
