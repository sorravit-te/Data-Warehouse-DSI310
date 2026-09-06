"""Interactive BI dashboard for Task 3.2 — OmniCorp unified Chinook/Northwind sales.

Built on the Kimball star schema documented in
``docs/task2/DIMENSIONAL_MODEL.md``: a single ``FactSales`` fact table (grain
= one row per sales transaction line item) plus five conformed dimensions
(``DimTime``, ``DimCustomer``, ``DimEmployee``, ``DimProduct``,
``DimSourceSystem``). Run with ``streamlit run app.py``.
"""

import pandas as pd
import streamlit as st

from app import queries
from app.data_loader import build_engines
from app.model import (
    build_dim_customer,
    build_dim_employee,
    build_dim_product,
    build_dim_source_system,
    build_dim_time,
    build_fact_sales,
)
from app.validation import DOCUMENTED_TOTALS, TOLERANCE

st.set_page_config(page_title="OmniCorp Unified Sales BI", page_icon="📊", layout="wide")

CATEGORY_COLORS = {
    "Chinook": "#eecf8c",
    "Northwind": "#5388d4",
    "Combined": "#0d9488",
}


def render_colored_metric(label: str, value: str, color: str) -> None:
    st.markdown(
        f"""
        <div style="border-left:6px solid {color}; padding:0.4rem 0.9rem; margin-bottom:0.25rem;">
            <div style="font-size:0.8rem;color:#555;">
                <span style="display:inline-block;width:10px;height:10px;
                border-radius:50%;background:{color};margin-right:6px;"></span>
                {label}
            </div>
            <div style="font-size:1.6rem;font-weight:600;color:#111;">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_resource(show_spinner="Connecting to source databases…")
def get_engines():
    return build_engines()


@st.cache_data(show_spinner="Building DimSourceSystem…")
def load_dim_source_system() -> pd.DataFrame:
    return build_dim_source_system()


@st.cache_data(show_spinner="Building DimCustomer…")
def load_dim_customer() -> pd.DataFrame:
    chinook_engine, northwind_engine = get_engines()
    return build_dim_customer(chinook_engine, northwind_engine)


@st.cache_data(show_spinner="Building DimEmployee…")
def load_dim_employee() -> pd.DataFrame:
    chinook_engine, northwind_engine = get_engines()
    return build_dim_employee(chinook_engine, northwind_engine)


@st.cache_data(show_spinner="Building DimProduct…")
def load_dim_product() -> pd.DataFrame:
    chinook_engine, northwind_engine = get_engines()
    return build_dim_product(chinook_engine, northwind_engine)


@st.cache_data(show_spinner="Building DimTime…")
def load_dim_time() -> pd.DataFrame:
    chinook_engine, northwind_engine = get_engines()
    return build_dim_time(chinook_engine, northwind_engine)


@st.cache_data(show_spinner="Building FactSales (this can take a moment on first run)…")
def load_fact_sales() -> pd.DataFrame:
    chinook_engine, northwind_engine = get_engines()
    return build_fact_sales(chinook_engine, northwind_engine)


def check_documented_totals(revenue_df: pd.DataFrame):
    lookup = dict(zip(revenue_df["SourceSystemName"], revenue_df["SalesAmount"]))
    chinook_total = lookup.get("Chinook", 0.0)
    northwind_total = lookup.get("Northwind", 0.0)
    computed = {
        "Chinook": chinook_total,
        "Northwind": northwind_total,
        "Combined": chinook_total + northwind_total,
    }
    matches = all(
        abs(computed[label] - DOCUMENTED_TOTALS[label]) <= TOLERANCE
        for label in DOCUMENTED_TOTALS
    )
    return matches, computed


dim_source_system = load_dim_source_system()
dim_customer = load_dim_customer()
dim_employee = load_dim_employee()
dim_product = load_dim_product()
dim_time = load_dim_time()
fact_sales = load_fact_sales()

fact_with_date = fact_sales.merge(dim_time[["DateKey", "FullDate"]], on="DateKey", how="left")

st.title("OmniCorp Unified Sales BI")
st.caption(
    "Chinook (music) + Northwind (food & beverage) unified into one FactSales "
    "star schema — see docs/task2/DIMENSIONAL_MODEL.md for the full contract."
)

st.sidebar.header("Filters")
source_options = dim_source_system["SourceSystemName"].tolist()
selected_sources = st.sidebar.multiselect(
    "Source system", source_options, default=source_options
)

min_date = fact_with_date["FullDate"].min().date()
max_date = fact_with_date["FullDate"].max().date()
date_range = st.sidebar.date_input(
    "Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date
)
if not isinstance(date_range, tuple) or len(date_range) != 2:
    date_range = (min_date, max_date)

is_default_filter = set(selected_sources) == set(source_options) and date_range == (
    min_date,
    max_date,
)

source_name_to_id = dict(zip(dim_source_system["SourceSystemName"], dim_source_system["SourceSystemID"]))
selected_ids = [source_name_to_id[name] for name in selected_sources]

filtered = fact_with_date[
    fact_with_date["SourceSystemID"].isin(selected_ids)
    & (fact_with_date["FullDate"] >= pd.Timestamp(date_range[0]))
    & (fact_with_date["FullDate"] <= pd.Timestamp(date_range[1]))
]

with st.expander("Fact Row Interpretation (Task 3.1)"):
    st.markdown("**Documented example — Northwind OrderID 10248 / ProductID 11:**")
    st.markdown(
        "> On July 4, 2016, one Northwind sales line item recorded customer Paul "
        "Henriot purchasing 12 unit(s) of Queso Cabrales for a SalesAmount of "
        "168.00, with the order attributed to Steven Buchanan (Sales Manager)."
    )
    st.divider()
    st.markdown("**Try another row** (picked from the current filtered FactSales rows):")
    if len(filtered) > 0:
        row_index = st.number_input(
            "Row index", min_value=0, max_value=len(filtered) - 1, value=0, step=1
        )
        picked_row = filtered.iloc[int(row_index)]
        st.markdown(
            "> "
            + queries.describe_fact_row(
                picked_row, dim_customer, dim_employee, dim_product, dim_time, dim_source_system
            )
        )
    else:
        st.info("No rows match the current filters.")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "Revenue by Source System",
        "Top Customers",
        "Top Products",
        "Employee Performance",
        "Analysis by Date",
        "Source System Comparison",
    ]
)

with tab1:
    st.subheader("Revenue: Music (Chinook) vs. Food & Beverage (Northwind)")
    revenue = queries.revenue_by_source(filtered, dim_source_system)

    metric_cols = st.columns(len(revenue) + 1)
    for col, (_, row) in zip(metric_cols, revenue.iterrows()):
        with col:
            render_colored_metric(
                row["SourceSystemName"],
                f"{row['SalesAmount']:,.2f}",
                CATEGORY_COLORS[row["SourceSystemName"]],
            )
    with metric_cols[-1]:
        render_colored_metric(
            "Combined", f"{revenue['SalesAmount'].sum():,.2f}", CATEGORY_COLORS["Combined"]
        )

    revenue_chart_df = revenue.copy()
    revenue_chart_df["Color"] = revenue_chart_df["SourceSystemName"].map(CATEGORY_COLORS)
    st.bar_chart(revenue_chart_df, x="SourceSystemName", y="SalesAmount", color="Color")

    st.divider()
    st.markdown("#### Average SalesAmount per Line Item")
    st.caption(
        "Raw totals above are dominated by the difference in transaction volume "
        "(2,240 Chinook line items vs. 609,283 Northwind line items). Average "
        "SalesAmount per line item normalizes for that, comparing how big a "
        "typical sale is in each business."
    )
    comparison = queries.source_system_comparison(filtered, dim_source_system)
    avg_cols = st.columns(len(comparison))
    for col, (_, row) in zip(avg_cols, comparison.iterrows()):
        with col:
            render_colored_metric(
                row["SourceSystemName"],
                f"{row['AvgLineValue']:,.2f}",
                CATEGORY_COLORS[row["SourceSystemName"]],
            )

    comparison_chart_df = comparison.copy()
    comparison_chart_df["Color"] = comparison_chart_df["SourceSystemName"].map(CATEGORY_COLORS)
    st.bar_chart(comparison_chart_df, x="SourceSystemName", y="AvgLineValue", color="Color")

    if is_default_filter:
        matches, computed = check_documented_totals(revenue)
        if matches:
            st.success("✓ Matches documented totals in docs/task3/BI_DASHBOARD_MOCKUP.md")
        else:
            st.error("✗ Does not match documented totals — check FactSales ETL logic")
        with st.expander("Documented vs. computed totals"):
            st.dataframe(
                pd.DataFrame(
                    {"Documented": DOCUMENTED_TOTALS, "Computed": computed}
                ).style.format("{:,.2f}")
            )
    else:
        st.caption(
            "Validation badge hidden while filters are active — a filtered "
            "subtotal will not match the documented whole-dataset totals."
        )

with tab2:
    st.subheader("Top 10 Customers by Spend")
    split_customers = st.checkbox("Split by source system", key="split_customers")
    st.dataframe(
        queries.top_customers(
            filtered, dim_customer, dim_source_system, n=10, split_by_source=split_customers
        ),
        width="stretch",
    )

with tab3:
    st.subheader("Top 10 Products / Tracks by Spend")
    st.dataframe(queries.top_products(filtered, dim_product, n=10), width="stretch")

with tab4:
    st.subheader("Employee Performance")
    st.warning(
        "Chinook employee attribution reflects the customer's assigned support "
        "representative (`Customer.SupportRepId`), not a salesperson recorded "
        "directly on the invoice. Northwind attribution is direct "
        "(`Orders.EmployeeID`)."
    )
    split_employees = st.checkbox("Split by source system", key="split_employees")
    st.dataframe(
        queries.employee_performance(
            filtered, dim_employee, dim_source_system, split_by_source=split_employees
        ),
        width="stretch",
    )

with tab5:
    st.subheader("Analysis by Date")
    granularity = st.selectbox("Granularity", ["Day", "Month", "Quarter", "Year"], index=1)
    split_time = st.checkbox("Split by source system", key="split_time")
    period_result = queries.sales_by_period(
        filtered, dim_time, dim_source_system, granularity=granularity, split_by_source=split_time
    )
    period_col = {"Day": "FullDate", "Month": "Month", "Quarter": "Quarter", "Year": "Year"}[
        granularity
    ]
    if split_time:
        chart_data = period_result.pivot(
            index=period_col, columns="SourceSystemName", values="SalesAmount"
        )
    else:
        chart_data = period_result.set_index(period_col)["SalesAmount"]
    st.bar_chart(chart_data)
    st.dataframe(period_result, width="stretch")

with tab6:
    st.subheader("Chinook vs. Northwind — Full Comparison")
    st.dataframe(
        queries.source_system_comparison(filtered, dim_source_system), width="stretch"
    )
