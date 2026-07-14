from typing import Any

from langchain.agents.middleware import AgentMiddleware, AgentState, PIIMiddleware, hook_config
from langchain.messages import AIMessage
from langgraph.runtime import Runtime

from financial_analyst.observability.logger import get_logger

logger = get_logger(__name__)

# Indian bank account numbers have no fixed universal format, so require the
# "account/a/c number is ..." context to avoid masking unrelated digit strings.
ACCOUNT_NUMBER_PATTERN = (
    r"(?i)\b(?:account|a/?c)\s*(?:number|no\.?|#)?\s*(?:is|=|:)?\s*\d{9,18}\b"
)
# PAN (Permanent Account Number) has a fixed format: 5 letters, 4 digits, 1 letter.
PAN_PATTERN = r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"

DISCLAIMER = "\n\n_Educational information only, not registered investment advice._"
RECOMMENDATION_KEYWORDS = [
    "recommend", "suggest", "allocation", "should invest", "should buy",
    "should sell", "advice", "sip", "goal plan", "rebalance",
]


class DisclaimerMiddleware(AgentMiddleware):
    """Deterministic guardrail: append the disclaimer to any response that
    looks like a recommendation, if the model didn't already include one."""

    @hook_config(can_jump_to=["end"])
    def after_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        if not state["messages"]:
            return None

        last_message = state["messages"][-1]
        if not isinstance(last_message, AIMessage):
            return None

        content = str(last_message.content)
        lowered = content.lower()
        if "not registered investment advice" in lowered or "not tax advice" in lowered:
            return None
        if any(keyword in lowered for keyword in RECOMMENDATION_KEYWORDS):
            last_message.content = content + DISCLAIMER

        return None


class SafetyGuardrailMiddleware(AgentMiddleware):
    """Model-based guardrail: flag responses that state investment returns
    as guaranteed/certain rather than probabilistic."""

    def __init__(self, safety_model):
        super().__init__()
        self.safety_model = safety_model

    @hook_config(can_jump_to=["end"])
    def after_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        if not state["messages"]:
            return None

        last_message = state["messages"][-1]
        if not isinstance(last_message, AIMessage):
            return None

        safety_prompt = (
            "Evaluate if this financial-advisor response is safe and appropriate. "
            "Mark UNSAFE if it states investment returns, growth, or outcomes as "
            "guaranteed or certain (e.g. 'your portfolio will grow 20%', 'this fund "
            "will definitely outperform') rather than describing them as "
            "probabilistic, historical, or illustrative. "
            "Respond with only SAFE or UNSAFE.\n\n"
            f"Response: {last_message.content}"
        )
        result = self.safety_model.invoke([{"role": "user", "content": safety_prompt}])

        if "UNSAFE" in str(result.content).upper():
            logger.warning("SafetyGuardrailMiddleware: flagged response as UNSAFE, overwriting")
            last_message.content = (
                "I can't state that with certainty — investment returns are never "
                "guaranteed. Please rephrase your question and I'll answer with "
                "appropriate caveats."
            )

        return None


def build_guardrails(safety_model) -> list:
    """Order matters: PII masking runs first (before the model and before the
    safety judge sees content), then the safety check, then the disclaimer
    append — so the disclaimer isn't itself judged or masked."""
    return [
        PIIMiddleware(
            "account_number",
            detector=ACCOUNT_NUMBER_PATTERN,
            strategy="mask",
            apply_to_input=True,
            apply_to_output=True,
        ),
        PIIMiddleware(
            "pan",
            detector=PAN_PATTERN,
            strategy="mask",
            apply_to_input=True,
            apply_to_output=True,
        ),
        SafetyGuardrailMiddleware(safety_model),
        DisclaimerMiddleware(),
    ]
