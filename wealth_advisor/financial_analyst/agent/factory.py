from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware

from financial_analyst.llm.factory import get_llm
from financial_analyst.agent.tools import build_memory_tools, build_goal_tools
from financial_analyst.agent.guardrails import build_guardrails
from financial_analyst.rag.retriever_tool import get_retrieval_tool
from financial_analyst.skills.skill_tools import load_skill, build_skills_prompt
from financial_analyst.mcp.mcp_client import get_mcp_tools
from financial_analyst.agent.market_data import build_market_data_tools
from financial_analyst.observability.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a personal financial advisor assistant for Indian retail investors.

Always call retrieval_tool before giving advice or citing a rule (SEBI/RBI/tax/fund info).
Use get_profile/get_portfolio/get_transactions/get_goal_history to check what you already
know about the user before asking them to repeat information. If something needed for
personalized advice is missing (e.g. risk tolerance), ask the user for it rather than
guessing.

Use get_holdings/get_ltp (from the broker) for the user's live holdings and last-traded
prices — prefer these over get_portfolio when the user asks for current/live figures,
since get_portfolio reflects the last uploaded CSV snapshot.

Use fetch_live_quote for public market prices/NAVs not in the user's own holdings
(e.g. a fund/stock they're considering buying), and fetch_news for recent headlines
about a symbol or topic. Both are best-effort — if they report data is unavailable,
say so rather than guessing a number.

If the user confirms they want a goal saved, call propose_goal — this requires their
explicit approval before it persists, so don't ask them to repeat the confirmation.

Always disclose that this is educational information, not registered investment advice.
Never state investment returns as guaranteed."""


async def build_agent(checkpointer, user_id: str):
    """Create the main financial-advisor agent: retrieval + long-term-memory +
    skill + broker (MCP) tools, gated by safety/PII guardrails and a HITL
    approval gate on propose_goal (the only tool that persists new data on
    the agent's own initiative)."""
    llm = get_llm()
    retrieval_tool = get_retrieval_tool()
    memory_tools = build_memory_tools(user_id)
    goal_tools = build_goal_tools(user_id)
    mcp_tools = await get_mcp_tools()
    market_data_tools = await build_market_data_tools()

    skills_prompt = build_skills_prompt()
    full_prompt = SYSTEM_PROMPT
    if skills_prompt:
        full_prompt = SYSTEM_PROMPT + "\n\n" + skills_prompt

    hitl_middleware = HumanInTheLoopMiddleware(
        interrupt_on={
            "propose_goal": {"allowed_decisions": ["approve", "reject"]},
        },
        description_prefix="Goal save pending approval",
    )

    return create_agent(
        llm,
        tools=[retrieval_tool, load_skill, *memory_tools, *goal_tools, *mcp_tools, *market_data_tools],
        system_prompt=full_prompt,
        middleware=[*build_guardrails(llm), hitl_middleware],
        checkpointer=checkpointer,
    )
