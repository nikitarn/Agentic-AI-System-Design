from __future__ import annotations

from pathlib import Path

from langchain.tools import tool

from financial_analyst.config import config
from financial_analyst.skills.registry import SkillRegistry, SkillNotFoundError
from financial_analyst.observability.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Singleton registry
# ---------------------------------------------------------------------------
# One SkillRegistry instance is shared for the entire process lifetime.
# Created lazily on the first call to get_registry() so Path.cwd() resolves
# to wherever `financial_analyst` was invoked from, not this package's dir.
# ---------------------------------------------------------------------------
_registry: SkillRegistry | None = None


def get_registry() -> SkillRegistry:
    """
    Return the process-wide SkillRegistry, building it on first call.

    skills_dir resolution order:
      1. Read "skills.skills_dir" from config.yaml -> e.g. ".skills"
      2. Resolve relative to Path.cwd()             -> wherever the CLI runs from
    """
    global _registry
    if _registry is None:
        skills_dir = Path.cwd() / config.get("skills", {}).get("skills_dir", ".skills")
        _registry = SkillRegistry(skills_dir)
        _registry.load()
        logger.info(f"SkillRegistry initialized from: {skills_dir}")
    return _registry


# ---------------------------------------------------------------------------
# Called by agent/factory.py at agent build time (not a tool — plain function)
# ---------------------------------------------------------------------------


def build_skills_prompt() -> str:
    """
    Trigger registry initialisation and return the metadata-only prompt snippet,
    appended to SYSTEM_PROMPT before the agent is created.
    """
    return get_registry().build_skills_prompt()


# ---------------------------------------------------------------------------
# The agent-callable tool (registered in agent/factory.py tools list)
# ---------------------------------------------------------------------------


@tool
def load_skill(name: str) -> str:
    """
    Load the full instructions for a skill by name.
    Call this when the user's request matches one of the skills listed in your
    system prompt (e.g. portfolio_analysis, portfolio_dashboard,
    sip_recommendation, tax_planning).
    """
    logger.info(f"Tool called: load_skill('{name}')")
    try:
        return get_registry().load_skill(name)
    except SkillNotFoundError as e:
        return str(e)
