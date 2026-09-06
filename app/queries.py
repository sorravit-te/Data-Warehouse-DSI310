"""BI-question aggregations from Section 10 of DIMENSIONAL_MODEL.md.

Every function here takes already-built dataframes (never engines), so they
work identically whether called from ``app.py`` (cached, Streamlit) or from
a quick script/REPL (uncached, plain pandas).
"""

import pandas as pd


def revenue_by_source(fact: pd.DataFrame, dim_source_system: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        fact.groupby("SourceSystemID")
        .agg(SalesAmount=("SalesAmount", "sum"), SalesQuantity=("SalesQuantity", "sum"))
        .reset_index()
    )
    result = grouped.merge(dim_source_system, on="SourceSystemID", how="left")
    return result[["SourceSystemName", "SalesAmount", "SalesQuantity"]].sort_values(
        "SourceSystemName"
    )


def top_customers(
    fact: pd.DataFrame,
    dim_customer: pd.DataFrame,
    dim_source_system: pd.DataFrame,
    n: int = 10,
    split_by_source: bool = False,
) -> pd.DataFrame:
    group_cols = ["CustomerID", "SourceSystemID"] if split_by_source else ["CustomerID"]
    grouped = (
        fact.groupby(group_cols)
        .agg(SalesAmount=("SalesAmount", "sum"), SalesQuantity=("SalesQuantity", "sum"))
        .reset_index()
    )
    result = grouped.merge(dim_customer, on="CustomerID", how="left")
    if split_by_source:
        result = result.merge(dim_source_system, on="SourceSystemID", how="left")

    display_cols = ["CustomerName", "CompanyName", "Country"]
    if split_by_source:
        display_cols.append("SourceSystemName")
    display_cols += ["SalesAmount", "SalesQuantity"]

    return result.sort_values("SalesAmount", ascending=False).head(n)[display_cols]


def top_products(
    fact: pd.DataFrame, dim_product: pd.DataFrame, n: int = 10
) -> pd.DataFrame:
    grouped = (
        fact.groupby("ProductID")
        .agg(SalesAmount=("SalesAmount", "sum"), SalesQuantity=("SalesQuantity", "sum"))
        .reset_index()
    )
    result = grouped.merge(dim_product, on="ProductID", how="left")
    display_cols = [
        "ProductName",
        "GenreName",
        "CategoryName",
        "SalesAmount",
        "SalesQuantity",
    ]
    return result.sort_values("SalesAmount", ascending=False).head(n)[display_cols]


def employee_performance(
    fact: pd.DataFrame,
    dim_employee: pd.DataFrame,
    dim_source_system: pd.DataFrame,
    split_by_source: bool = False,
) -> pd.DataFrame:
    scoped = fact[fact["EmployeeID"].notna()]
    group_cols = ["EmployeeID", "SourceSystemID"] if split_by_source else ["EmployeeID"]
    grouped = (
        scoped.groupby(group_cols)
        .agg(SalesAmount=("SalesAmount", "sum"), SalesQuantity=("SalesQuantity", "sum"))
        .reset_index()
    )
    result = grouped.merge(dim_employee, on="EmployeeID", how="left")
    if split_by_source:
        result = result.merge(dim_source_system, on="SourceSystemID", how="left")

    display_cols = ["EmployeeName", "Title"]
    if split_by_source:
        display_cols.append("SourceSystemName")
    display_cols += ["SalesAmount", "SalesQuantity"]

    return result.sort_values("SalesAmount", ascending=False)[display_cols]


_GRANULARITY_COLUMNS = {
    "Day": "FullDate",
    "Month": "Month",
    "Quarter": "Quarter",
    "Year": "Year",
}


def sales_by_period(
    fact: pd.DataFrame,
    dim_time: pd.DataFrame,
    dim_source_system: pd.DataFrame,
    granularity: str = "Month",
    split_by_source: bool = False,
) -> pd.DataFrame:
    period_col = _GRANULARITY_COLUMNS[granularity]
    merged = fact.merge(dim_time, on="DateKey", how="left")
    if split_by_source:
        merged = merged.merge(dim_source_system, on="SourceSystemID", how="left")

    group_cols = [period_col, "SourceSystemName"] if split_by_source else [period_col]
    grouped = (
        merged.groupby(group_cols)
        .agg(SalesAmount=("SalesAmount", "sum"), SalesQuantity=("SalesQuantity", "sum"))
        .reset_index()
    )
    return grouped.sort_values(period_col)


def source_system_comparison(
    fact: pd.DataFrame, dim_source_system: pd.DataFrame
) -> pd.DataFrame:
    grouped = (
        fact.groupby("SourceSystemID")
        .agg(
            SalesAmount=("SalesAmount", "sum"),
            SalesQuantity=("SalesQuantity", "sum"),
            TransactionCount=("SalesAmount", "size"),
        )
        .reset_index()
    )
    grouped["AvgLineValue"] = grouped["SalesAmount"] / grouped["TransactionCount"]
    result = grouped.merge(dim_source_system, on="SourceSystemID", how="left")
    return result[
        [
            "SourceSystemName",
            "SalesAmount",
            "SalesQuantity",
            "TransactionCount",
            "AvgLineValue",
        ]
    ].sort_values("SourceSystemName")


def describe_fact_row(
    row: pd.Series,
    dim_customer: pd.DataFrame,
    dim_employee: pd.DataFrame,
    dim_product: pd.DataFrame,
    dim_time: pd.DataFrame,
    dim_source_system: pd.DataFrame,
) -> str:
    """Render one FactSales row as the Task 3.1 English sentence, joining all 5 dimensions."""
    customer = dim_customer.loc[dim_customer["CustomerID"] == row["CustomerID"]]
    product = dim_product.loc[dim_product["ProductID"] == row["ProductID"]]
    time_row = dim_time.loc[dim_time["DateKey"] == row["DateKey"]]
    source = dim_source_system.loc[
        dim_source_system["SourceSystemID"] == row["SourceSystemID"]
    ]

    customer_name = customer["CustomerName"].iloc[0] if not customer.empty else "an unknown customer"
    product_name = product["ProductName"].iloc[0] if not product.empty else "an unknown product"
    full_date = (
        time_row["FullDate"].iloc[0].strftime("%B %-d, %Y")
        if not time_row.empty
        else str(row["DateKey"])
    )
    source_name = source["SourceSystemName"].iloc[0] if not source.empty else "an unknown source"

    sentence = (
        f"On {full_date}, one {source_name} sales line item recorded customer "
        f"{customer_name} purchasing {int(row['SalesQuantity'])} unit(s) of "
        f"{product_name} for a SalesAmount of {row['SalesAmount']:,.2f}"
    )

    if pd.notna(row["EmployeeID"]):
        employee = dim_employee.loc[dim_employee["EmployeeID"] == row["EmployeeID"]]
        if not employee.empty:
            employee_name = employee["EmployeeName"].iloc[0]
            title = employee["Title"].iloc[0]
            title_part = f" ({title})" if pd.notna(title) else ""
            sentence += f", with the order attributed to {employee_name}{title_part}."
        else:
            sentence += "."
    else:
        sentence += "."

    return sentence
