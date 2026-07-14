"""Deterministic (no-LLM) allocation-drift check.

target_allocation() mirrors the age-bracket table in
knowledge_base/docs/retirement_and_sip_playbook.md ("Asset Allocation by
Age") — keep the two in sync if either changes.
"""

# (low_age, high_age, conservative_equity_range, aggressive_equity_range)
AGE_BRACKETS = [
    (25, 35, (65, 75), (75, 85)),
    (36, 45, (55, 65), (65, 75)),
    (46, 55, (45, 55), (55, 65)),
    (56, 65, (35, 45), (45, 55)),
    (66, 200, (0, 35), (0, 45)),
]

# Our holdings data only tags type as stock/mutual_fund, with no fund-category
# field to distinguish equity vs. debt mutual funds. Stocks are always equity;
# a mutual fund is classified as debt only if its name mentions one of these
# keywords, otherwise it's treated as equity. This is a heuristic forced by
# the data model, not a real fund-category lookup — revisit if holdings ever
# gain a proper category field.
DEBT_KEYWORDS = ("bond", "debt", "liquid", "gilt", "money market")

DRIFT_THRESHOLD_PP = 7.0


def _is_debt(holding: dict) -> bool:
    if holding["type"] == "stock":
        return False
    name = (holding.get("name") or holding.get("symbol") or "").lower()
    return any(keyword in name for keyword in DEBT_KEYWORDS)


def compute_allocation(holdings: list[dict]) -> dict[str, float]:
    """Current portfolio split into equity % / debt %, market-value weighted,
    so it's directly comparable to target_allocation()'s equity/debt split."""
    if not holdings:
        return {}
    total = sum(h["quantity"] * h["current_price"] for h in holdings)
    if total == 0:
        return {}
    debt_value = sum(h["quantity"] * h["current_price"] for h in holdings if _is_debt(h))
    equity_value = total - debt_value
    return {
        "equity": round(equity_value / total * 100, 2),
        "debt": round(debt_value / total * 100, 2),
    }


def target_allocation(profile: dict | None) -> dict[str, float]:
    """Lookup-table target equity/debt split by age bracket + risk tolerance.
    Falls back to age=35/risk=medium if profile fields are missing."""
    age = (profile or {}).get("age") or 35
    risk = ((profile or {}).get("risk_tolerance") or "medium").lower()

    for low, high, conservative_range, aggressive_range in AGE_BRACKETS:
        if low <= age <= high:
            equity_range = aggressive_range if risk == "high" else conservative_range
            equity_pct = sum(equity_range) / 2
            return {"equity": round(equity_pct, 2), "debt": round(100 - equity_pct, 2)}

    return {"equity": 50.0, "debt": 50.0}


def drift(current: dict[str, float], target: dict[str, float]) -> dict[str, float]:
    """Per-category percentage-point gap: current - target."""
    categories = set(current) | set(target)
    return {
        category: round(current.get(category, 0.0) - target.get(category, 0.0), 2)
        for category in categories
    }


def flagged_categories(drift_result: dict[str, float], threshold: float = DRIFT_THRESHOLD_PP) -> list[str]:
    """Categories whose drift exceeds the rebalance threshold."""
    return [category for category, gap in drift_result.items() if abs(gap) > threshold]
