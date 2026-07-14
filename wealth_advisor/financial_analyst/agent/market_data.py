from langchain.agents import create_agent
from langchain.tools import tool
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware
from langchain_mcp_adapters.client import MultiServerMCPClient

from financial_analyst.llm.factory import get_llm
from financial_analyst.observability.logger import get_logger

logger = get_logger(__name__)

_MARKET_DATA_SYSTEM_PROMPT = """You are a narrow browsing agent for fetching public market data.

You may ONLY navigate to these URLs:
- https://www.amfiindia.com/spages/NAVAll.txt (mutual fund NAVs — plain text, one line per scheme)
- https://www.google.com/finance/quote/<SYMBOL>:<EXCHANGE> (stock quotes, e.g. TCS:NSE, RELIANCE:NSE)
- https://news.google.com/search?q=<QUERY> (public news search — headlines only)

Rules:
- Never navigate anywhere else. Never log in. Never submit any form.
- For NAV lookups: find the line matching the fund/scheme name and extract the NAV value and date.
- For stock quotes: extract the current price and currency.
- For news: extract 3-5 recent headline + source + date; do not open individual articles.
- If you can't find a clean answer, say so explicitly rather than guessing.
"""


async def _build_market_data_agent():
    client = MultiServerMCPClient(
        {
            "playwright": {
                "command": "npx",
                "args": ["-y", "@playwright/mcp@latest"],
                "transport": "stdio",
            }
        }
    )
    tools = await client.get_tools()
    llm = get_llm()
    return create_agent(
        llm,
        tools=tools,
        system_prompt=_MARKET_DATA_SYSTEM_PROMPT,
        middleware=[
            ModelCallLimitMiddleware(run_limit=8, exit_behavior="end"),
            ToolCallLimitMiddleware(tool_name="browser_navigate", run_limit=3, exit_behavior="end"),
        ],
    )


async def build_market_data_tools() -> list:
    """Build fetch_live_quote/fetch_news, backed by a narrow Playwright
    sub-agent restricted to public NAV/quote/news pages. Both tools are
    best-effort: scraping failures return a clear fallback string instead
    of raising, so a broken page never blocks the main agent's response."""
    market_data_agent = await _build_market_data_agent()

    @tool
    async def fetch_live_quote(symbol_or_scheme: str) -> str:
        """Fetch a live stock quote or mutual fund NAV from public sources
        (Google Finance / AMFI). Best-effort — falls back to a clear
        'unavailable' message if the page structure changed or the symbol
        can't be matched, rather than erroring."""
        logger.info(f"Tool called: fetch_live_quote({symbol_or_scheme})")
        try:
            result = await market_data_agent.ainvoke({
                "messages": [
                    {"role": "user", "content": f"Fetch the current live price/NAV for: {symbol_or_scheme}"}
                ]
            })
            return str(result["messages"][-1].content)
        except Exception as e:
            logger.warning(f"fetch_live_quote failed for {symbol_or_scheme}: {e}")
            return "Live price unavailable, using last uploaded price."

    @tool
    async def fetch_news(symbol_or_topic: str) -> str:
        """Fetch 3-5 recent public news headlines for a symbol/topic via
        Google News search. Best-effort — falls back to a clear
        'unavailable' message rather than erroring."""
        logger.info(f"Tool called: fetch_news({symbol_or_topic})")
        try:
            result = await market_data_agent.ainvoke({
                "messages": [
                    {"role": "user", "content": f"Fetch 3-5 recent news headlines about: {symbol_or_topic}"}
                ]
            })
            return str(result["messages"][-1].content)
        except Exception as e:
            logger.warning(f"fetch_news failed for {symbol_or_topic}: {e}")
            return "News unavailable right now."

    return [fetch_live_quote, fetch_news]
