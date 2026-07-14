# NSE / BSE Stock Symbol Reference

> Educational reference content, not registered investment advice.

## Symbol Format

- **NSE (National Stock Exchange)** — symbols are alphabetic tickers, no
  fixed length, usually an abbreviation of the company name (e.g.
  `RELIANCE`, `TCS`, `INFY`). Quoted as `NSE:SYMBOL` in most data feeds and
  charting tools (e.g. `NSE:INFY`).
- **BSE (Bombay Stock Exchange)** — symbols are **numeric scrip codes**
  (e.g. Reliance Industries is `500325` on BSE), though BSE also assigns a
  short alphabetic mnemonic for display purposes. Most retail platforms
  default to showing the NSE ticker even for BSE-listed-only companies.
- A company listed on both exchanges (the vast majority of large caps) will
  have **two different identifiers** — an NSE alphabetic ticker and a BSE
  numeric scrip code — referring to the same underlying share.
- Large-cap classification (SEBI-aligned): roughly the **top 100 companies
  by full market capitalization** across NSE/BSE.

This is the doc the **lexical_retrieval** (BM25) tool should win on for
queries containing an exact symbol like `NSE:INFY` or `HDFCBANK` — exact
string matches beat semantic similarity here.

## Sample Ticker Table

| NSE Symbol   | Company                          | Sector              | Exchange(s) |
|--------------|-----------------------------------|----------------------|--------------|
| RELIANCE     | Reliance Industries Ltd           | Energy/Conglomerate   | NSE, BSE     |
| TCS          | Tata Consultancy Services         | IT Services           | NSE, BSE     |
| INFY         | Infosys Ltd                       | IT Services           | NSE, BSE     |
| HDFCBANK     | HDFC Bank Ltd                     | Banking                | NSE, BSE     |
| ICICIBANK    | ICICI Bank Ltd                    | Banking                | NSE, BSE     |
| ITC          | ITC Ltd                           | FMCG                    | NSE, BSE     |
| HINDUNILVR   | Hindustan Unilever Ltd            | FMCG                    | NSE, BSE     |
| SBIN         | State Bank of India                | Banking                | NSE, BSE     |
| BHARTIARTL   | Bharti Airtel Ltd                  | Telecom                 | NSE, BSE     |
| LT           | Larsen & Toubro Ltd                | Infrastructure/Capital Goods | NSE, BSE |
| KOTAKBANK    | Kotak Mahindra Bank Ltd            | Banking                | NSE, BSE     |
| AXISBANK     | Axis Bank Ltd                      | Banking                | NSE, BSE     |
| ASIANPAINT   | Asian Paints Ltd                   | Consumer Durables       | NSE, BSE     |
| MARUTI       | Maruti Suzuki India Ltd            | Automobile              | NSE, BSE     |
| SUNPHARMA    | Sun Pharmaceutical Industries      | Pharmaceuticals         | NSE, BSE     |
| TATAMOTORS   | Tata Motors Ltd                    | Automobile              | NSE, BSE     |
| WIPRO        | Wipro Ltd                          | IT Services             | NSE, BSE     |
| ULTRACEMCO   | UltraTech Cement Ltd               | Cement                  | NSE, BSE     |
| NTPC         | NTPC Ltd                           | Power/Energy            | NSE, BSE     |
| ADANIENT     | Adani Enterprises Ltd              | Diversified/Infrastructure | NSE, BSE  |

Prices/quotes above are intentionally omitted — they change continuously
during market hours; use `fetch_live_quote` for a current NAV/quote rather
than treating anything in this file as a live price.

## Notes for Recommendations

- When a user references a company by common name ("Infosys", "HDFC Bank"),
  resolve it to its NSE symbol before calling `fetch_live_quote` or citing a
  company report — the sample `company_reports_sample/` docs are keyed by
  symbol, not company name.
- Sector concentration matters for portfolio analysis: if a user's holdings
  cluster heavily in one sector from this table (e.g. multiple banking
  names), that's a concentration-risk flag per SEBI's investor-protection
  guidance in `sebi_rules.md`.
