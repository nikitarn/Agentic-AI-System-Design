import pandas as pd


def load_statement(csv_path: str) -> list[dict]:
    """Load a bank statement CSV into normalized transaction records."""
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    for col in ("debit", "credit", "balance"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df.to_dict(orient="records")


if __name__ == "__main__":
    import sys
    from pprint import pprint

    rows = load_statement(sys.argv[1])
    print(f"Loaded {len(rows)} transactions\n")
    pprint(rows[:3])
    print("...")
    pprint(rows[-3:])
