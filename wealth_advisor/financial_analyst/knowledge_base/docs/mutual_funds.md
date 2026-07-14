# Mutual Fund Basics: Categories, Plans, and NAV

> Educational reference content, not registered investment advice.

## Categories (Recap)

Every scheme falls into one SEBI-defined category — see `sebi_rules.md` for
the full categorization rules. The broad groups relevant for portfolio
analysis:

- **Equity** — Large Cap, Mid Cap, Small Cap, Flexi Cap, ELSS, Sectoral/
  Thematic, etc. Higher volatility, higher long-run return potential.
- **Debt** — Liquid, Short/Medium/Long Duration, Corporate Bond, Gilt, etc.
  Lower volatility, income-oriented.
- **Hybrid** — a mix of equity and debt in one scheme (Conservative Hybrid,
  Aggressive Hybrid, Multi Asset Allocation, etc.).
- **Index Funds / ETFs** — passively track an index (e.g. Nifty 50, Sensex)
  at a much lower expense ratio than actively managed funds.

## Direct vs. Regular Plans

Every scheme is sold in two plan variants that hold the **same underlying
portfolio** but differ in cost:

- **Direct plan** — bought straight from the AMC (app/website), no
  distributor commission baked in. Lower **expense ratio**, so more of the
  return reaches the investor.
- **Regular plan** — bought through a distributor/broker/advisor, who earns
  a trail commission embedded in the expense ratio.
- The gap is typically **0.5–1.0% per year for equity funds** and
  **0.1–0.5% per year for debt funds**. Over a long horizon (10+ years) this
  compounds into a meaningfully different final corpus even though both
  plans invest identically.
- A **direct plan's NAV is always higher than its regular-plan twin** for
  the same scheme — this is purely a cost artifact, not a sign the direct
  plan has performed better in absolute terms; growth *rate* is what's
  actually faster.

## NAV Mechanics

- **NAV (Net Asset Value)** = (total value of the fund's holdings −
  liabilities and expenses) ÷ number of outstanding units.
- NAV is calculated **once per business day**, after markets close, using
  that day's closing prices of the fund's holdings.
- The **expense ratio (TER — Total Expense Ratio)** is deducted daily from
  the fund's assets before NAV is struck — investors don't pay it as a
  separate bill, it's already reflected in the NAV they see.
- Because NAV already nets out expenses, comparing raw NAV *levels* across
  funds tells you nothing about quality — a ₹15 NAV fund isn't "cheaper" or
  "better value" than a ₹150 NAV fund. What matters is NAV **growth over
  time** and the expense ratio itself.

## Sample Fund Reference Table

Illustrative sample set spanning categories — useful for symbol/code lookup
during retrieval testing. Treat scheme-code strings like `AXISBLUECHIP` and
`PARAGPARIKHFLEXICAP` as the kind of exact-match string the lexical
(BM25) retriever should win on, versus a fuzzy question like "what's a good
large cap fund" which the semantic retriever should handle.

| Sample Code                | Fund Name (illustrative)              | Category         | AMC                    |
|-----------------------------|----------------------------------------|-------------------|--------------------------|
| AXISBLUECHIP                | Axis Bluechip Fund                     | Large Cap          | Axis Mutual Fund         |
| PARAGPARIKHFLEXICAP          | Parag Parikh Flexi Cap Fund            | Flexi Cap          | PPFAS Mutual Fund        |
| HDFCFLEXICAP                 | HDFC Flexi Cap Fund                    | Flexi Cap          | HDFC Mutual Fund         |
| SBISMALLCAP                  | SBI Small Cap Fund                     | Small Cap          | SBI Mutual Fund          |
| ICICIPRUBLUECHIP              | ICICI Prudential Bluechip Fund         | Large Cap          | ICICI Prudential         |
| MIRAEASSETLARGECAP             | Mirae Asset Large Cap Fund             | Large Cap          | Mirae Asset              |
| CANARAROBECOBLUECHIP            | Canara Robeco Bluechip Equity Fund     | Large Cap          | Canara Robeco            |
| JMFLEXICAP                       | JM Flexicap Fund                       | Flexi Cap          | JM Financial             |
| AXISELSS                          | Axis Long Term Equity Fund (ELSS)      | ELSS               | Axis Mutual Fund         |
| QUANTMIDCAP                        | Quant Mid Cap Fund                     | Mid Cap            | Quant Mutual Fund        |
| ICICIPRUCORPORATEBOND                | ICICI Prudential Corporate Bond Fund   | Debt — Corporate Bond | ICICI Prudential      |
| HDFCLIQUID                             | HDFC Liquid Fund                       | Debt — Liquid       | HDFC Mutual Fund         |
| SBIGILTFUND                              | SBI Magnum Gilt Fund                   | Debt — Gilt         | SBI Mutual Fund          |
| ICICIPRUEQUITYSAVINGS                     | ICICI Prudential Equity Savings Fund   | Hybrid — Equity Savings | ICICI Prudential     |
| UTINIFTYINDEX                              | UTI Nifty 50 Index Fund                | Index/ETF           | UTI Mutual Fund          |

Names above are real, publicly known schemes used for realistic lexical
matching — not a recommendation to buy any of them, and NAV/AUM figures
change daily so none are hardcoded here; use `fetch_live_quote` for current
values.
