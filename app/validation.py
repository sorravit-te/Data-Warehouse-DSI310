"""Acceptance check: FactSales totals must match docs/task3/BI_DASHBOARD_MOCKUP.md.

Run standalone with ``python -m app.validation`` from the repo root. This
bypasses Streamlit's caching entirely so it can be iterated on quickly while
building ``app/model.py``.
"""

from app.data_loader import build_engines
from app.model import build_fact_sales

DOCUMENTED_TOTALS = {
    "Chinook": 2328.60,
    "Northwind": 448475298.72,
    "Combined": 448477627.32,
}

TOLERANCE = 0.01


def compute_totals():
    chinook_engine, northwind_engine = build_engines()
    fact = build_fact_sales(chinook_engine, northwind_engine)

    by_source = fact.groupby("SourceSystemID")["SalesAmount"].sum()
    chinook_total = float(by_source.get(1, 0.0))
    northwind_total = float(by_source.get(2, 0.0))
    combined_total = float(fact["SalesAmount"].sum())

    return {
        "Chinook": chinook_total,
        "Northwind": northwind_total,
        "Combined": combined_total,
    }


def assert_documented_totals() -> None:
    computed = compute_totals()
    mismatches = []
    for label, documented in DOCUMENTED_TOTALS.items():
        actual = computed[label]
        if abs(actual - documented) > TOLERANCE:
            mismatches.append(
                f"{label}: expected {documented:,.2f}, got {actual:,.2f} "
                f"(diff {actual - documented:,.2f})"
            )

    if mismatches:
        raise AssertionError(
            "FactSales totals do not match documented figures:\n"
            + "\n".join(mismatches)
        )

    for label, value in computed.items():
        print(f"{label}: {value:,.2f} (matches documented {DOCUMENTED_TOTALS[label]:,.2f})")


if __name__ == "__main__":
    assert_documented_totals()
    print("All documented totals match.")
