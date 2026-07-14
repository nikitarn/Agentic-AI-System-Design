from mcp.server.fastmcp import FastMCP

from financial_analyst.memory import portfolio_store
from financial_analyst.observability.logger import get_logger

logger = get_logger(__name__)

mcp = FastMCP("broker_mock")

# Single-user system for now — matches CURRENT_USER in main.py. Reads from the
# same portfolio_store the CLI's /upload_portfolio writes to, so this stands
# in for a real broker API without a second, independently-drifting data source.
DEFAULT_USER = "default_user"


@mcp.tool()
def get_holdings() -> list[dict]:
    """Read-only: return the user's current holdings (stocks, mutual funds).
    No order placement — this is a mock broker for advisory purposes only."""
    holdings = portfolio_store.get_portfolio(DEFAULT_USER)
    logger.info(f"MCP tool called: get_holdings -> {len(holdings)} holdings")
    return holdings


@mcp.tool()
def get_ltp(symbol: str) -> dict:
    """Read-only: return the last traded price for a held symbol.
    No order placement — this is a mock broker for advisory purposes only."""
    holdings = portfolio_store.get_portfolio(DEFAULT_USER)
    match = next((h for h in holdings if h["symbol"].upper() == symbol.upper()), None)
    logger.info(f"MCP tool called: get_ltp({symbol}) -> {'found' if match else 'not found'}")
    if not match:
        return {"symbol": symbol, "error": "Symbol not found in holdings."}
    return {"symbol": match["symbol"], "ltp": match["current_price"]}


if __name__ == "__main__":
    mcp.run(transport="stdio")
