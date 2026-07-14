import json
from datetime import datetime, timezone

from pydantic import BaseModel
from langchain.agents import create_agent

from financial_analyst.llm.factory import get_llm
from financial_analyst.memory import watchlist_store, portfolio_store, profile_store
from financial_analyst.analysis.rebalance import compute_allocation, target_allocation, drift
from financial_analyst.rag.retriever_tool import get_retrieval_tool
from financial_analyst.agent.market_data import build_market_data_tools
from financial_analyst.observability.logger import get_logger

logger = get_logger(__name__)


class HoldingRecommendation(BaseModel):
    symbol: str
    action: str  # buy / sell / hold / rebalance
    rationale: str
    confidence: str  # low / medium / high
    evidence: list[str]  # doc/news snippets cited


class WeeklyReviewResult(BaseModel):
    recommendations: list[HoldingRecommendation]
    overall_rebalancing_note: str


_SYSTEM_PROMPT = """You are a financial analyst producing a weekly portfolio review.

Given price changes, news, and allocation drift for a user's watchlist, produce
one HoldingRecommendation per watchlist symbol (action: buy/sell/hold/rebalance)
plus one overall_rebalancing_note.

Rules:
- Base rationale on the provided price/news/drift/tax context, not speculation.
- Never state returns as guaranteed — describe them as probabilistic/illustrative.
- confidence should be "low" if evidence is thin (e.g. no news, small price move).
- evidence should cite specific inputs you were given (a price % change, a
  headline, a drift percentage, a tax rule) — not generic statements.
- This is educational information, not registered investment advice.
"""


async def _safety_check(llm, review: WeeklyReviewResult) -> WeeklyReviewResult:
    """Same UNSAFE-detection judgment as SafetyGuardrailMiddleware
    (agent/guardrails.py), applied to this structured result before saving —
    the middleware itself is built for conversational agent state, so this
    reimplements the same check for a non-conversational structured call."""
    combined_text = review.overall_rebalancing_note + "\n" + "\n".join(
        r.rationale for r in review.recommendations
    )
    safety_prompt = (
        "Evaluate if this financial-advisor text is safe and appropriate. "
        "Mark UNSAFE if it states investment returns/outcomes as guaranteed or "
        "certain rather than probabilistic/illustrative. "
        "Respond with only SAFE or UNSAFE.\n\n"
        f"Text: {combined_text}"
    )
    result = await llm.ainvoke([{"role": "user", "content": safety_prompt}])
    if "UNSAFE" in str(result.content).upper():
        logger.warning("Weekly review flagged UNSAFE by safety check — withholding rationale text")
        review.overall_rebalancing_note = (
            "Recommendations withheld pending review — flagged for overly certain language."
        )
        for rec in review.recommendations:
            rec.rationale = "Withheld pending review."
    return review


async def run(user_id: str) -> WeeklyReviewResult:
    """One weekly-review pass for a single user: price fetch, drift calc,
    one batched LLM call, safety check, save to watchlist_store."""
    watchlist_symbols = watchlist_store.get_watchlist(user_id)
    if not watchlist_symbols:
        logger.info(f"No watchlist symbols for {user_id}, skipping review")
        return WeeklyReviewResult(
            recommendations=[],
            overall_rebalancing_note="No symbols on watchlist yet — use /watch <symbol> or /upload_portfolio.",
        )

    holdings = portfolio_store.get_portfolio(user_id)
    holdings_by_symbol = {h["symbol"]: h for h in holdings}

    market_data_tools = await build_market_data_tools()
    fetch_live_quote = next(t for t in market_data_tools if t.name == "fetch_live_quote")
    fetch_news = next(t for t in market_data_tools if t.name == "fetch_news")

    as_of = datetime.now(timezone.utc).isoformat()
    price_deltas: dict[str, float] = {}
    movers: list[str] = []
    quote_narratives: dict[str, str] = {}

    for symbol in watchlist_symbols:
        if symbol in holdings_by_symbol:
            # Reliable numeric price source: the last uploaded/synced holding price.
            current_price = holdings_by_symbol[symbol]["current_price"]
            watchlist_store.record_price(symbol, current_price, as_of)
            history = watchlist_store.get_price_history(symbol, days=7)
            if len(history) > 1:
                prior_price = history[1]["price"]  # [0] is the one just inserted
                if prior_price:
                    pct_change = (current_price - prior_price) / prior_price * 100
                    price_deltas[symbol] = round(pct_change, 2)
                    if abs(pct_change) > 5:
                        movers.append(symbol)
        else:
            # No numeric price source for a manually-watched symbol not in
            # holdings — best-effort narrative quote instead of a hard number.
            quote_narratives[symbol] = await fetch_live_quote.ainvoke(
                {"symbol_or_scheme": symbol}
            )

    for symbol in movers:
        news_text = await fetch_news.ainvoke({"symbol_or_topic": symbol})
        prefix = quote_narratives.get(symbol, "")
        quote_narratives[symbol] = (prefix + "\nRecent news:\n" + news_text).strip()

    profile = profile_store.get_profile(user_id)
    current_alloc = compute_allocation(holdings) if holdings else {}
    target_alloc = target_allocation(profile) if profile else {}
    drift_result = drift(current_alloc, target_alloc) if current_alloc and target_alloc else {}

    retrieval_tool = get_retrieval_tool()
    tax_context = retrieval_tool.invoke(
        "capital gains tax considerations for selling stocks and mutual funds held under 1 year in India"
    )

    llm = get_llm()
    review_agent = create_agent(
        llm, tools=[], system_prompt=_SYSTEM_PROMPT, response_format=WeeklyReviewResult
    )

    prompt = (
        f"Watchlist symbols: {watchlist_symbols}\n"
        f"Week-over-week price changes (%) for holdings: {price_deltas}\n"
        f"Symbols that moved >5%: {movers}\n"
        f"Live quotes / news context for watched-but-not-held or moved symbols: {quote_narratives}\n"
        f"Current portfolio allocation (equity/debt %): {current_alloc}\n"
        f"Target allocation for this user's age/risk profile: {target_alloc}\n"
        f"Allocation drift (percentage points, current - target): {drift_result}\n"
        f"Tax considerations for selling: {tax_context}\n\n"
        "Produce one HoldingRecommendation per watchlist symbol plus one "
        "overall_rebalancing_note."
    )
    result = await review_agent.ainvoke({"messages": [{"role": "user", "content": prompt}]})
    review: WeeklyReviewResult = result["structured_response"]
    review = await _safety_check(llm, review)

    week_of = datetime.now(timezone.utc).date().isoformat()
    for rec in review.recommendations:
        watchlist_store.save_recommendation(
            user_id=user_id,
            symbol=rec.symbol,
            week_of=week_of,
            action=rec.action,
            rationale=rec.rationale,
            confidence=rec.confidence,
            evidence=json.dumps(rec.evidence),
            price_at_time=holdings_by_symbol.get(rec.symbol, {}).get("current_price"),
        )
    logger.info(f"Weekly review complete for {user_id}: {len(review.recommendations)} recommendations")
    return review
