"""Interactive BI dashboard for Task 3.2 — OmniCorp unified Chinook/Northwind sales.

Built on the Kimball star schema documented in
``docs/task2/DIMENSIONAL_MODEL.md``: a single ``FactSales`` fact table (grain
= one row per sales transaction line item) plus five conformed dimensions
(``DimTime``, ``DimCustomer``, ``DimEmployee``, ``DimProduct``,
``DimSourceSystem``). Run with ``streamlit run app.py``.
"""

import altair as alt
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


def render_comparison_chart(df: pd.DataFrame, category_col: str, value_col: str, y_title: str) -> None:
    """Bar chart (true-to-scale) colored per CATEGORY_COLORS, plus a
    log-scale dot chart underneath when one category's value dwarfs the
    other's — the bar chart alone leaves the smaller business's bar
    visually zero (e.g. Chinook's 2,328.60 next to Northwind's
    448,475,298.72), so the dot chart is added for a comparable view. A bar
    mark can't be reused for that: Vega-Lite bars always extend to a zero
    baseline, which is undefined for log(0), so dots are used instead."""
    categories = df[category_col].tolist()
    values = df[value_col]
    use_log_view = (values > 0).all() and values.max() / values.min() >= 20
    color_scale = alt.Scale(domain=categories, range=[CATEGORY_COLORS[c] for c in categories])

    def base(scale: alt.Scale) -> alt.Chart:
        return alt.Chart(df).encode(
            x=alt.X(f"{category_col}:N", title=None, sort=categories),
            y=alt.Y(f"{value_col}:Q", title=y_title, scale=scale),
            color=alt.Color(f"{category_col}:N", scale=color_scale, legend=alt.Legend(title=None)),
            tooltip=[
                alt.Tooltip(f"{category_col}:N", title="Source"),
                alt.Tooltip(f"{value_col}:Q", title=y_title, format=",.2f"),
            ],
        )

    bar_chart = base(alt.Scale(type="linear", zero=True)).mark_bar().properties(height=320)
    st.altair_chart(bar_chart, width="stretch")

    if use_log_view:
        st.caption(
            "Bar chart drawn to true scale — the smaller business's bar may "
            "be nearly invisible here. The log-scale dot chart below keeps "
            "both businesses visible for comparison; see the metric cards "
            "above for exact values."
        )
        dot_chart = base(alt.Scale(type="log")).mark_circle(size=500).properties(height=320)
        st.altair_chart(dot_chart, width="stretch")


def render_ranked_bar_chart(
    df: pd.DataFrame, label_col: str, value_col: str, color_col: str | None = None
) -> None:
    """Horizontal bar chart for ranked lists (top customers/employees) — labels
    read left-to-right on the y-axis instead of being rotated on the x-axis."""
    order = df.sort_values(value_col, ascending=False)[label_col].tolist()
    encoding = {
        "y": alt.Y(f"{label_col}:N", sort=order, title=None),
        "x": alt.X(f"{value_col}:Q", title=value_col),
        "tooltip": [
            alt.Tooltip(f"{label_col}:N", title="Name"),
            alt.Tooltip(f"{value_col}:Q", title=value_col, format=",.2f"),
        ],
    }
    if color_col:
        categories = [c for c in df[color_col].dropna().unique().tolist()]
        encoding["color"] = alt.Color(
            f"{color_col}:N",
            scale=alt.Scale(
                domain=categories, range=[CATEGORY_COLORS.get(c, "#94a3b8") for c in categories]
            ),
            legend=alt.Legend(title=None),
        )
    else:
        encoding["color"] = alt.value(CATEGORY_COLORS["Northwind"])

    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(**encoding)
        .properties(height=max(220, 28 * len(df)))
    )
    st.altair_chart(chart, width="stretch")


def render_product_scatter(df: pd.DataFrame) -> None:
    """Scatter plot of quantity vs. revenue per product — a different chart
    shape from the ranked bars above, showing whether a product's revenue
    comes from high volume or a high per-unit price."""
    df = df.copy()
    df["Classification"] = df["GenreName"].fillna(df["CategoryName"]).fillna("Unclassified")

    def padded_domain(series: pd.Series) -> list[float]:
        lo, hi = series.min(), series.max()
        margin = (hi - lo) * 0.1 or hi * 0.1 or 1
        return [lo - margin, hi + margin]

    chart = (
        alt.Chart(df)
        .mark_circle(size=200)
        .encode(
            x=alt.X(
                "SalesQuantity:Q",
                title="SalesQuantity",
                scale=alt.Scale(domain=padded_domain(df["SalesQuantity"])),
            ),
            y=alt.Y(
                "SalesAmount:Q",
                title="SalesAmount",
                scale=alt.Scale(domain=padded_domain(df["SalesAmount"])),
            ),
            color=alt.Color("Classification:N", legend=alt.Legend(title="Genre / Category")),
            tooltip=[
                alt.Tooltip("ProductName:N", title="Product"),
                alt.Tooltip("Classification:N"),
                alt.Tooltip("SalesQuantity:Q", format=","),
                alt.Tooltip("SalesAmount:Q", format=",.2f"),
            ],
        )
        .properties(height=360)
    )
    st.altair_chart(chart, width="stretch")


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

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Revenue by Source System",
        "Top Customers",
        "Top Products",
        "Employee Performance",
        "Analysis by Date",
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

    render_comparison_chart(revenue, "SourceSystemName", "SalesAmount", "SalesAmount")
    st.markdown(
        "*Business takeaway: Northwind (food & beverage) accounts for virtually "
        "all of OmniCorp's combined revenue in the current dataset, while Chinook "
        "(music) contributes a negligible share. This reflects each business's "
        "transaction volume in the source data (609,283 vs. 2,240 line items) — "
        "it is not evidence that one business model is inherently more profitable "
        "per sale.*"
    )

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

    render_comparison_chart(comparison, "SourceSystemName", "AvgLineValue", "AvgLineValue")
    st.markdown(
        "*Business takeaway: a typical Northwind sale (≈$736 per line item) is "
        "far larger than a typical Chinook sale (≈$1.04 per line item), because "
        "Northwind orders are bulk food/beverage purchases (multiple units per "
        "line) while Chinook sales are single-track music purchases. Normalizing "
        "by line item — rather than looking at raw totals — is what actually "
        "lets a business analyst compare how big a typical sale is between the "
        "two acquired businesses.*"
    )

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
    top_customers_df = queries.top_customers(
        filtered, dim_customer, dim_source_system, n=10, split_by_source=split_customers
    )
    render_ranked_bar_chart(
        top_customers_df,
        "CustomerName",
        "SalesAmount",
        color_col="SourceSystemName" if split_customers else None,
    )
    st.dataframe(top_customers_df, width="stretch")

with tab3:
    st.subheader("Top 10 Products / Tracks by Spend")
    top_products_df = queries.top_products(filtered, dim_product, n=10)
    render_product_scatter(top_products_df)
    st.caption(
        "Each point is one product: further right means higher unit volume, "
        "further up means higher revenue. A product far up but not far right "
        "earns its revenue from a high per-unit price rather than volume."
    )
    st.dataframe(top_products_df, width="stretch")

with tab4:
    st.subheader("Employee Performance")
    st.warning(
        "Chinook employee attribution reflects the customer's assigned support "
        "representative (`Customer.SupportRepId`), not a salesperson recorded "
        "directly on the invoice. Northwind attribution is direct "
        "(`Orders.EmployeeID`)."
    )
    split_employees = st.checkbox("Split by source system", key="split_employees")
    employee_performance_df = queries.employee_performance(
        filtered, dim_employee, dim_source_system, split_by_source=split_employees
    )
    render_ranked_bar_chart(
        employee_performance_df,
        "EmployeeName",
        "SalesAmount",
        color_col="SourceSystemName" if split_employees else None,
    )
    st.dataframe(employee_performance_df, width="stretch")

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
