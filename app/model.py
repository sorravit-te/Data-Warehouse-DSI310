"""Build the unified FactSales fact table and its five conformed dimensions.

Every transformation here follows the contract documented in
``docs/task2/DIMENSIONAL_MODEL.md`` (mirrored row-by-row in
``docs/task1/source_to_target_mapping.csv``). This module is plain pandas /
SQLAlchemy with no Streamlit dependency so it can be exercised directly from
``app/validation.py`` without a Streamlit runtime.
"""

import pandas as pd
from sqlalchemy.engine import Engine

FACT_SALES_COLUMNS = [
    "DateKey",
    "CustomerID",
    "EmployeeID",
    "ProductID",
    "SourceSystemID",
    "SalesQuantity",
    "SalesAmount",
]

DIM_CUSTOMER_COLUMNS = [
    "CustomerID",
    "CustomerName",
    "CompanyName",
    "City",
    "State",
    "Country",
    "PostalCode",
    "Phone",
    "Email",
]

DIM_EMPLOYEE_COLUMNS = [
    "EmployeeID",
    "EmployeeName",
    "Title",
    "City",
    "Country",
    "ReportsTo",
]

DIM_PRODUCT_COLUMNS = [
    "ProductID",
    "ProductName",
    "CategoryName",
    "GenreName",
    "Composer",
    "UnitPrice",
]

DIM_TIME_COLUMNS = [
    "DateKey",
    "FullDate",
    "DayOfMonth",
    "DayOfWeek",
    "Month",
    "Quarter",
    "Year",
]


def _add_prefix(series: pd.Series, prefix: str) -> pd.Series:
    """Vectorized ``PREFIX:<id>`` construction that keeps NULLs as NA.

    Handles both numeric source columns (Chinook's INTEGER ids, normalized
    through nullable Int64 so ``5`` does not become ``"5.0"``) and text
    source columns (Northwind's TEXT ids, e.g. ``CustomerID = "VINET"``).
    """
    if pd.api.types.is_numeric_dtype(series):
        base = series.astype("Int64").astype("string")
    else:
        base = series.astype("string")
    return (prefix + base).mask(series.isna())


def _compute_date_key(date_series: pd.Series) -> pd.Series:
    """Derive a nullable YYYYMMDD integer key; never fabricates missing dates."""
    parsed = pd.to_datetime(date_series, errors="coerce")
    date_key_text = parsed.dt.strftime("%Y%m%d")
    return pd.to_numeric(date_key_text, errors="coerce").astype("Int64")


def build_dim_source_system() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "SourceSystemID": [1, 2],
            "SourceSystemName": ["Chinook", "Northwind"],
        }
    )


def build_dim_customer(chinook_engine: Engine, northwind_engine: Engine) -> pd.DataFrame:
    chinook_raw = pd.read_sql_query(
        """
        SELECT CustomerId, FirstName, LastName, Company, City, State,
               Country, PostalCode, Phone, Email
        FROM Customer
        """,
        chinook_engine,
    )
    chinook_dim = pd.DataFrame(
        {
            "CustomerID": _add_prefix(chinook_raw["CustomerId"], "CHINOOK:"),
            "CustomerName": (
                chinook_raw["FirstName"].fillna("").str.strip()
                + " "
                + chinook_raw["LastName"].fillna("").str.strip()
            ).str.strip(),
            "CompanyName": chinook_raw["Company"],
            "City": chinook_raw["City"],
            "State": chinook_raw["State"],
            "Country": chinook_raw["Country"],
            "PostalCode": chinook_raw["PostalCode"],
            "Phone": chinook_raw["Phone"],
            "Email": chinook_raw["Email"],
        }
    )

    northwind_raw = pd.read_sql_query(
        """
        SELECT CustomerID, ContactName, CompanyName, City, Region,
               Country, PostalCode, Phone
        FROM Customers
        """,
        northwind_engine,
    )
    northwind_dim = pd.DataFrame(
        {
            "CustomerID": _add_prefix(northwind_raw["CustomerID"], "NORTHWIND:"),
            "CustomerName": northwind_raw["ContactName"],
            "CompanyName": northwind_raw["CompanyName"],
            "City": northwind_raw["City"],
            "State": northwind_raw["Region"],
            "Country": northwind_raw["Country"],
            "PostalCode": northwind_raw["PostalCode"],
            "Phone": northwind_raw["Phone"],
            "Email": pd.NA,
        }
    )

    return pd.concat(
        [chinook_dim[DIM_CUSTOMER_COLUMNS], northwind_dim[DIM_CUSTOMER_COLUMNS]],
        ignore_index=True,
    )


def build_dim_employee(chinook_engine: Engine, northwind_engine: Engine) -> pd.DataFrame:
    chinook_raw = pd.read_sql_query(
        "SELECT EmployeeId, FirstName, LastName, Title, City, Country, ReportsTo FROM Employee",
        chinook_engine,
    )
    chinook_dim = pd.DataFrame(
        {
            "EmployeeID": _add_prefix(chinook_raw["EmployeeId"], "CHINOOK:"),
            "EmployeeName": (
                chinook_raw["FirstName"].fillna("").str.strip()
                + " "
                + chinook_raw["LastName"].fillna("").str.strip()
            ).str.strip(),
            "Title": chinook_raw["Title"],
            "City": chinook_raw["City"],
            "Country": chinook_raw["Country"],
            "ReportsTo": _add_prefix(chinook_raw["ReportsTo"], "CHINOOK:"),
        }
    )

    northwind_raw = pd.read_sql_query(
        "SELECT EmployeeID, FirstName, LastName, Title, City, Country, ReportsTo FROM Employees",
        northwind_engine,
    )
    northwind_dim = pd.DataFrame(
        {
            "EmployeeID": _add_prefix(northwind_raw["EmployeeID"], "NORTHWIND:"),
            "EmployeeName": (
                northwind_raw["FirstName"].fillna("").str.strip()
                + " "
                + northwind_raw["LastName"].fillna("").str.strip()
            ).str.strip(),
            "Title": northwind_raw["Title"],
            "City": northwind_raw["City"],
            "Country": northwind_raw["Country"],
            "ReportsTo": _add_prefix(northwind_raw["ReportsTo"], "NORTHWIND:"),
        }
    )

    return pd.concat(
        [chinook_dim[DIM_EMPLOYEE_COLUMNS], northwind_dim[DIM_EMPLOYEE_COLUMNS]],
        ignore_index=True,
    )


def build_dim_product(chinook_engine: Engine, northwind_engine: Engine) -> pd.DataFrame:
    chinook_raw = pd.read_sql_query(
        """
        SELECT t.TrackId, t.Name AS ProductName, t.Composer, t.UnitPrice,
               g.Name AS GenreName
        FROM Track t
        LEFT JOIN Genre g ON t.GenreId = g.GenreId
        """,
        chinook_engine,
    )
    chinook_dim = pd.DataFrame(
        {
            "ProductID": _add_prefix(chinook_raw["TrackId"], "CHINOOK:"),
            "ProductName": chinook_raw["ProductName"],
            "CategoryName": pd.NA,
            "GenreName": chinook_raw["GenreName"],
            "Composer": chinook_raw["Composer"],
            "UnitPrice": chinook_raw["UnitPrice"],
        }
    )

    northwind_raw = pd.read_sql_query(
        """
        SELECT p.ProductID, p.ProductName, p.UnitPrice, c.CategoryName
        FROM Products p
        LEFT JOIN Categories c ON p.CategoryID = c.CategoryID
        """,
        northwind_engine,
    )
    northwind_dim = pd.DataFrame(
        {
            "ProductID": _add_prefix(northwind_raw["ProductID"], "NORTHWIND:"),
            "ProductName": northwind_raw["ProductName"],
            "CategoryName": northwind_raw["CategoryName"],
            "GenreName": pd.NA,
            "Composer": pd.NA,
            "UnitPrice": northwind_raw["UnitPrice"],
        }
    )

    return pd.concat(
        [chinook_dim[DIM_PRODUCT_COLUMNS], northwind_dim[DIM_PRODUCT_COLUMNS]],
        ignore_index=True,
    )


def build_dim_time(chinook_engine: Engine, northwind_engine: Engine) -> pd.DataFrame:
    """One row per distinct calendar date across both sources (not per transaction)."""
    chinook_dates = pd.read_sql_query(
        "SELECT DISTINCT date(InvoiceDate) AS d FROM Invoice", chinook_engine
    )["d"]
    northwind_dates = pd.read_sql_query(
        "SELECT DISTINCT date(OrderDate) AS d FROM Orders", northwind_engine
    )["d"]

    all_dates = pd.to_datetime(
        pd.concat([chinook_dates, northwind_dates], ignore_index=True).dropna().unique()
    )

    dim_time = pd.DataFrame({"FullDate": all_dates})
    dim_time["DateKey"] = dim_time["FullDate"].dt.strftime("%Y%m%d").astype(int)
    dim_time["DayOfMonth"] = dim_time["FullDate"].dt.day
    dim_time["DayOfWeek"] = dim_time["FullDate"].dt.day_name()
    dim_time["Month"] = dim_time["FullDate"].dt.month
    dim_time["Quarter"] = dim_time["FullDate"].dt.quarter
    dim_time["Year"] = dim_time["FullDate"].dt.year

    return dim_time[DIM_TIME_COLUMNS].sort_values("DateKey").reset_index(drop=True)


def build_fact_sales(chinook_engine: Engine, northwind_engine: Engine) -> pd.DataFrame:
    """Grain: one row per sales transaction line item (InvoiceLine / Order Details)."""
    chinook_raw = pd.read_sql_query(
        """
        SELECT i.InvoiceDate, i.CustomerId,
               c.SupportRepId AS EmployeeId,
               il.TrackId, il.UnitPrice, il.Quantity
        FROM InvoiceLine il
        JOIN Invoice i ON il.InvoiceId = i.InvoiceId
        JOIN Customer c ON i.CustomerId = c.CustomerId
        """,
        chinook_engine,
    )
    chinook_fact = pd.DataFrame(
        {
            "DateKey": _compute_date_key(chinook_raw["InvoiceDate"]),
            "CustomerID": _add_prefix(chinook_raw["CustomerId"], "CHINOOK:"),
            "EmployeeID": _add_prefix(chinook_raw["EmployeeId"], "CHINOOK:"),
            "ProductID": _add_prefix(chinook_raw["TrackId"], "CHINOOK:"),
            "SourceSystemID": 1,
            "SalesQuantity": chinook_raw["Quantity"].astype(int),
            "SalesAmount": chinook_raw["UnitPrice"].astype(float)
            * chinook_raw["Quantity"].astype(float),
        }
    )

    # Northwind Order Details.Discount is intentionally never selected here,
    # so it is structurally impossible for it to leak into SalesAmount.
    northwind_raw = pd.read_sql_query(
        """
        SELECT o.OrderDate, o.CustomerID, o.EmployeeID,
               od.ProductID, od.UnitPrice, od.Quantity
        FROM "Order Details" od
        JOIN Orders o ON od.OrderID = o.OrderID
        """,
        northwind_engine,
    )
    northwind_fact = pd.DataFrame(
        {
            "DateKey": _compute_date_key(northwind_raw["OrderDate"]),
            "CustomerID": _add_prefix(northwind_raw["CustomerID"], "NORTHWIND:"),
            "EmployeeID": _add_prefix(northwind_raw["EmployeeID"], "NORTHWIND:"),
            "ProductID": _add_prefix(northwind_raw["ProductID"], "NORTHWIND:"),
            "SourceSystemID": 2,
            "SalesQuantity": northwind_raw["Quantity"].astype(int),
            "SalesAmount": northwind_raw["UnitPrice"].astype(float)
            * northwind_raw["Quantity"].astype(float),
        }
    )

    return pd.concat(
        [chinook_fact[FACT_SALES_COLUMNS], northwind_fact[FACT_SALES_COLUMNS]],
        ignore_index=True,
    )
