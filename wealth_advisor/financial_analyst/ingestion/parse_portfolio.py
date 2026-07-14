import pandas as pd


def load_portfolio(csv_path: str) -> list[dict]:
    """Load a holdings CSV, cast numerics, and add per-holding P&L + market value."""
    df = pd.read_csv(csv_path)
    for col in ("quantity", "avg_price", "current_price"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["market_value"] = (df["current_price"] * df["quantity"]).round(2)
    df["pnl"] = ((df["current_price"] - df["avg_price"]) * df["quantity"]).round(2)
    return df.to_dict(orient="records")


def allocation_by_type(holdings: list[dict]) -> dict[str, float]:
    """Overall allocation % by holding type (e.g. stock vs mutual_fund)."""
    total = sum(h["market_value"] for h in holdings)
    totals_by_type: dict[str, float] = {}
    for h in holdings:
        totals_by_type[h["type"]] = totals_by_type.get(h["type"], 0.0) + h["market_value"]
    return {t: round(v / total * 100, 2) for t, v in totals_by_type.items()}


if __name__ == "__main__":
    import sys
    from pprint import pprint

    holdings = load_portfolio(sys.argv[1])
    print(f"Loaded {len(holdings)} holdings\n")
    pprint(holdings)
    print("\nAllocation by type:")
    pprint(allocation_by_type(holdings))
