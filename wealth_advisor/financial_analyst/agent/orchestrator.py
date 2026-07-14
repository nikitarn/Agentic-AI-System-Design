from langgraph.types import Command

from financial_analyst.observability.logger import get_logger

logger = get_logger(__name__)


async def handle_query(agent, question: str, thread_id: str) -> str:
    """Entry point for all user queries — invokes the agent with conversation
    memory, resolving any HITL approval interrupts along the way."""
    logger.info(f"Handling query for session {thread_id}: {question}")
    agent_config = {"configurable": {"thread_id": thread_id}}
    try:
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": question}]},
            config=agent_config,
            version="v2",
        )
        result = await _handle_interrupts(agent, result, agent_config)
        return result["messages"][-1].content
    except Exception as e:
        logger.error(f"Agent error: {e}")
        return f"Error: {e}"


async def _handle_interrupts(agent, result, agent_config: dict) -> dict:
    """HumanInTheLoopMiddleware pauses the graph (an "interrupt") whenever a
    gated tool call (e.g. propose_goal) needs a human decision. Keep resolving
    interrupts and resuming the agent until it finishes without asking for
    anything else."""
    while getattr(result, "interrupts", None):
        interrupt = result.interrupts[0]
        payload = interrupt.value
        action_requests = payload.get("action_requests", [])
        review_configs = payload.get("review_configs", [])

        if not action_requests:
            break

        decisions = []
        for index, action in enumerate(action_requests):
            tool_name = action.get("name", "unknown_tool")
            arguments = action.get("args", {})
            allowed = review_configs[index].get("allowed_decisions", ["approve", "reject"])

            print(f"\nApproval needed for tool: {tool_name}")
            print(f"Arguments: {arguments}")
            print(f"Allowed decisions: {', '.join(allowed)}")

            choice = input("Decision: ").strip().lower()
            while choice not in allowed:
                choice = input(f"Choose one of {allowed}: ").strip().lower()

            if choice == "approve":
                decisions.append({"type": "approve"})
            elif choice == "reject":
                feedback = input("Rejection feedback (optional): ").strip()
                decision = {"type": "reject"}
                if feedback:
                    decision["message"] = feedback
                decisions.append(decision)

        result = await agent.ainvoke(
            Command(resume={"decisions": decisions}),
            config=agent_config,
            version="v2",
        )
    return result
