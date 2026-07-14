# Test Examples — Retrieval vs. Memory

Example `/ask` queries for exercising each path through the agent
(`financial_analyst/agent/factory.py`). Run `financial_analyst`, then
`/set_profile` and `/upload_portfolio` first so the memory examples have
data to work with.

## Pure semantic retrieval (conceptual, no exact term)

```
/ask what is a good low-risk fund for a 3-year goal
/ask how does SEBI categorize mutual funds
/ask how is LTCG taxed on equity mutual funds
```

Routes to `semantic_retrieval` (dense/Chroma) inside `retrieval_tool`.

## Pure lexical retrieval (exact codes/symbols)

```
/ask what sector is AXISBLUECHIP
/ask what category is PARAGPARIKHFLEXICAP
/ask what does Section 80C cover
```

Routes to `lexical_retrieval` (BM25) inside `retrieval_tool`.

## Pure long-term memory (profile/portfolio/transactions)

```
/ask what is my risk tolerance
/ask what's my P&L on TCS
/ask how much did I spend on food delivery last month
```

Calls `get_profile` / `get_portfolio` / `get_transactions` directly —
no `retrieval_tool` call, since these need no knowledge-base content.

## Mixed — both in one question

```
/ask what is my risk tolerance and how much do I have in mutual funds
```

Calls both `get_profile` and `get_portfolio` in the same turn.

```
/ask given my risk tolerance, is my current allocation appropriate
```

Calls `retrieval_tool` (semantic) for allocation guidance. If risk
tolerance/portfolio were already established earlier in the conversation,
the agent may reuse that instead of re-calling the memory tools — good
test of short-term memory reuse vs. redundant tool calls.

## Short-term (cross-turn) memory

```
/ask what's my P&L on TCS
/ask and what about INFY
```

The second question only makes sense if the agent remembers turn 1.

## Full stress test — all three in one session

```
/set_profile risk=high
/upload_portfolio financial_analyst/knowledge_base/sample_data/sample_portfolio.csv
/ask is my portfolio too conservative for someone with high risk tolerance, and what does SEBI say about risk-o-meter categories
```

Should hit `get_profile`, `get_portfolio`, and `retrieval_tool` (semantic)
all in a single turn.

## Goal planning (`/set_goal`)

Different goal phrasings exercise different `target_type` values the planner
infers (`growth_pct` / `retirement` / `target_amount`):

```
/set_goal I want to see 20% portfolio growth in the next 12 months
/set_goal Help me retire in 20 years with a corpus of 2 crore
/set_goal Save 10 lakhs for a house down payment in 3 years
/set_goal Help me plan tax-saving investments for this financial year under Section 80C
```

After the plan renders as a table, try each approval path:

- **Approve**: type `A` — plan is saved via `goal_store.save_goal` +
  `save_goal_plan(approved=True)`; confirm with `/history`.
- **Modify**: type `M`, then a step ID from the table (e.g. `step_001`),
  then a new description, then `A` to approve the edited plan.
- **Reject**: type `R` — nothing is persisted (verify the row count in
  `goals` doesn't change, e.g. `sqlite3 .memory/memory.db "SELECT COUNT(*) FROM goals;"`
  before and after).

```
/history
```

Should list every *approved* goal saved so far, each with its target type/value/horizon.

## HITL interrupts (`agent/orchestrator.py`)

These exercise `_handle_interrupts` specifically — the loop that pauses the
agent on `propose_goal` and resumes it once you respond. Unlike `/set_goal`
(its own Rich-table approval loop), these go through the agent conversationally,
so the LLM must first parse your goal into `propose_goal`'s structured args
(`description`, `target_type`, `target_value`, `horizon_months`) before the
interrupt fires.

### Baseline — no interrupt at all

```
/ask what is my risk tolerance
```

Confirm this returns immediately with no "Approval needed for tool" prompt —
`_handle_interrupts`'s `while getattr(result, "interrupts", None)` loop should
exit on the first check since there's nothing to approve.

### Approve

```
/ask save a goal to reach a 50 lakh target amount in 5 years, call it house fund
```
then at the prompt:
```
approve
```

Check the tool call succeeded and persisted:
```
sqlite3 .memory/memory.db "SELECT COUNT(*) FROM goals;"
```
(run before and after — count should go up by 1).

### Reject, with feedback

```
/ask save a goal to grow my portfolio by 30% in 6 months, call it aggressive growth
```
then:
```
reject
too risky, not now
```

Confirm: the goal count does **not** change, and the agent's final response
acknowledges the rejection (it receives your feedback as the rejection reason).

### Reject, no feedback

Same as above but press enter with no text at the "Rejection feedback
(optional)" prompt — confirms the empty-string branch in
`_handle_interrupts` (`if feedback: decision["message"] = feedback`) doesn't
crash when feedback is skipped.

### Multiple goals, multiple interrupts in one session

```
/ask save a goal to reach a 30 lakh target amount in 2 years for a car
approve
/ask also save a retirement goal targeting a 1 crore corpus in 15 years
approve
/history
```

Confirms the interrupt loop resets correctly between separate `/ask` calls in
the same session (each is a fresh `handle_query` call, but same `thread_id`/
conversation).

### Malformed / ambiguous goal phrasing

```
/ask save a goal but I'm not sure about the numbers yet
```

Worth checking what happens if the LLM can't confidently fill in
`target_type`/`target_value`/`horizon_months` — it may ask a clarifying
question instead of calling `propose_goal` at all (no interrupt fires), or it
may call the tool with a best-guess value. Either is fine, but check which one
your model actually does.

## Broker MCP tools (`mcp_servers/broker_mock_server.py`)

`get_holdings` / `get_ltp` are served over MCP (a subprocess spawned at agent
startup) rather than being plain Python tools like the rest — worth checking
they're actually being used, not just `get_portfolio`.

```
/upload_portfolio financial_analyst/knowledge_base/sample_data/sample_portfolio.csv
/ask what is the live last-traded price for TCS from the broker
/ask what is the ltp for axisbluechip
/ask show me my holdings from the broker
/ask what is the LTP for FAKESTOCK from the broker
```

- The first two confirm `get_ltp` is called (log line: `MCP tool called:
  get_ltp(<SYMBOL>) -> found`) and that symbol matching is case-insensitive
  (`axisbluechip` still resolves).
- Third confirms `get_holdings` returns the full list.
- Fourth confirms the not-found path returns a clean error dict instead of
  crashing (`-> not found` in the logs, and the agent reports it gracefully
  rather than hallucinating a price).

Also worth testing that the agent picks `get_ltp` over `get_portfolio` when
asked for "live"/"current" price, per the system prompt in `agent/factory.py`:

```
/ask what is the current live price on RELIANCE
```

Check the logs show `get_ltp` was called, not `get_portfolio`.

Note: since the mock broker deliberately reads from the same `portfolio_store`
as `get_portfolio` (single source of truth — see the design discussion before
this was built), there's currently no actual live-vs-snapshot divergence for
the model to detect. A "does live differ from my upload" question will get
answered as "they match" without a real comparison happening — that's an
artifact of the mock data source, not a broken tool call.



### Confirming the MCP server itself is running

At startup, look for:
```
financial_analyst.mcp.mcp_client | Connecting to MCP servers: ['broker_mock']
financial_analyst.mcp.mcp_client | Loaded 2 tools from MCP servers
```

If this doesn't appear, or shows 0 tools, the subprocess in
`mcp_servers.json` failed to start — check `${PYTHON_EXECUTABLE}` resolved to
a Python that has `mcp`/`langchain-mcp-adapters` installed (the same
interpreter running `financial_analyst` itself).

## Live market data (`agent/market_data.py`)

Backed by a *second* MCP subprocess (`npx @playwright/mcp@latest`), spawned
at agent startup alongside the broker mock — expect slower startup than
usual. Both tools are best-effort: on failure they return a fallback string
instead of raising, so failures here should never crash the app.

**Known rough edge (as of last test):** the AMFI NAV lookup did not
successfully resolve a scheme — the sub-agent reported "unable to fetch"
without even raising an exception, most likely because AMFI's `NAVAll.txt`
is a huge plain-text file with tens of thousands of scheme lines that a
browser-snapshot-based agent struggles to grep through. Google Finance quote
lookups are more likely to succeed (small, structured page) but weren't
confirmed clean either — that attempt hit an OpenAI rate limit
(`429`, 30000/30000 TPM) from heavy testing that day, not a code issue. Retest
both once quota resets, before trusting either path.

```
/ask what is the live NAV for AXISBLUECHIP from AMFI
/ask what is the live stock price for TCS on Google Finance
/ask what's the latest news on Reliance Industries
```

Check the logs for:
```
financial_analyst.agent.market_data | Tool called: fetch_live_quote(<SYMBOL>)
financial_analyst.agent.market_data | Tool called: fetch_news(<SYMBOL>)
financial_analyst.agent.market_data | fetch_live_quote failed for <SYMBOL>: <error>   <- only on failure
```

If `fetch_live_quote`/`fetch_news` never even get called (no "Tool called"
line despite the question clearly being about live prices/news), check that
`build_market_data_tools()` actually made it into the tools list in
`agent/factory.py` and that `npx @playwright/mcp@latest` resolves — run
`npx -y @playwright/mcp@latest --version` standalone to confirm.

Also worth checking the safety caps don't get silently exceeded: the
sub-agent has `ModelCallLimitMiddleware(run_limit=8)` and
`ToolCallLimitMiddleware(tool_name="browser_navigate", run_limit=3)` — a
query that would require lots of back-and-forth browsing should cut off
cleanly (`exit_behavior="end"`) rather than loop indefinitely. Hard to
trigger deliberately without a deeper/messier query, but worth keeping in
mind if a market-data call ever takes unusually long.

## Freshness layer (`/watch`, `/run_weekly_review`, `/digest`, `--weekly-review`)

Full pipeline: `/watch` → `watchlist_store` → `weekly_review.run()` → LLM
recommendations → `/digest`. Start from a clean-ish state so the numbers are
easy to follow (a portfolio already uploaded, e.g. via the examples above).

### 1. Add a symbol you don't currently hold

```
/watch NIFTYBEES
```

Confirms `watchlist_store.add_to_watchlist` — this symbol has no price in
`portfolio_store`, so it'll take the `fetch_live_quote` fallback path in
`weekly_review.py` (narrative quote instead of a numeric price) rather than
the reliable holdings-based path.

### 2. Run the review manually (don't wait for Friday)

```
/run_weekly_review
```

Watch the logs for the full chain: `fetch_live_quote(NIFTYBEES)` (the
watched-but-not-held symbol), the `retrieval_tool` call for tax context, then
one `Using LLM provider` call for the structured `WeeklyReviewResult`, then a
`Saved recommendation for default_user/<SYMBOL>` line per watchlist symbol
(should be one per holding + NIFTYBEES). Confirm the printed
`overall_rebalancing_note` references your actual drift number (compare
against `/ask what's my current asset allocation`).

### 3. View the digest

```
/digest
```

Should list every recommendation just saved, one line per symbol, with
action/confidence/rationale.

### 4. Run it again — confirm /digest only shows what's new

```
/run_weekly_review
/digest
/digest
```

`/digest` marks everything it displays as reviewed (`watchlist_store.mark_reviewed`),
so the first `/digest` after a run shows that run's recommendations, and the
second `/digest` right after should show "No review pending." — not the same
list twice. Confirm with:
```
sqlite3 .memory/memory.db "SELECT status, COUNT(*) FROM recommendations GROUP BY status;"
```
(count should be all `reviewed`, none `pending`, after viewing).

### 5. The standalone/scheduled path

```
financial_analyst --weekly-review
```

Run this from a separate terminal (it exits after one pass, no REPL). Confirms
`main.py`'s `--weekly-review` flag routes to `scheduler.run_weekly_review_all_users()`
rather than the interactive `_run_async()` loop — check the process exits on
its own instead of hanging on a prompt.

### 6. Deterministic drift, independent of the LLM parts

```
/ask what's my current asset allocation and how far is it from target
```

This exercises `rebalance.py` directly through the agent's `portfolio_analysis`
skill — useful to sanity-check the drift numbers `weekly_review.py` is basing
its narration on, without spending an LLM call on the full review pipeline.

### Empty watchlist edge case

If you haven't uploaded a portfolio or `/watch`ed anything:
```
/run_weekly_review
```
Should return immediately with "No symbols on watchlist yet..." and zero
recommendations saved — confirms the early-return in `weekly_review.run()`
([`analysis/weekly_review.py:75-81`](financial_analyst/analysis/weekly_review.py)),
not a full (wasted) LLM call.

## Verifying which path was taken

Tail the logs while testing — each path logs distinctly:

```
financial_analyst.rag.retriever_tool | [retrieval_tool] Routing query: '...'
financial_analyst.rag.retriever_tool | [semantic_retrieval] '...' -> N chunks
financial_analyst.rag.retriever_tool | [lexical_retrieval] '...' -> N chunks
financial_analyst.agent.tools | Tool called: get_profile (...)
financial_analyst.agent.tools | Tool called: get_portfolio (...)
financial_analyst.agent.tools | Tool called: get_transactions (...)
__main__ | MCP tool called: get_holdings (...)
__main__ | MCP tool called: get_ltp(<SYMBOL>) -> found / not found
```
