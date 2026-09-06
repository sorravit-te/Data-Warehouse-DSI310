# Data Warehouse : DSI310

Unified analytical data warehouse design for Chinook and Northwind.

## Project Overview

OmniCorp has acquired two businesses represented by separate SQLite databases: Chinook, a digital music store, and Northwind, a food, beverage, and product-sales business. Their schemas were designed independently, so equivalent business concepts use different table names, structures, datatypes, identifiers, and relationships.

This project analyzes both source systems and designs one unified analytical Data Warehouse. The model supports business intelligence questions such as:

- How does revenue compare between the music and food/product businesses?
- Who are the top customers by total spend?
- Which products or tracks are the top sellers?
- How does sales performance vary by employee?
- How do sales vary over time and by source system?

The repository covers source understanding, Source-to-Target Mapping, dimensional modeling, a business-readable fact-row expression, a BI report mock-up, and data engineering design considerations. It defines the analytical model and its transformation contracts; it does not implement a complete production ETL platform or production Data Lake.

## Data Sources

### Chinook

Chinook represents digital music sales. Its relevant sales path is:

```text
Customer -> Invoice -> InvoiceLine -> Track -> Genre
```

`InvoiceLine` contains the line quantity, unit price, and track reference. The `Invoice` header provides the customer and transaction date. Chinook invoices do not contain a direct employee identifier. Employee context is derived through:

```text
Customer.SupportRepId -> Employee.EmployeeId
```

This relationship identifies the customer's assigned support representative, not a salesperson recorded directly on an invoice.

### Northwind

Northwind represents food, beverage, and other product sales. Its relevant sales path is:

```text
Customers -> Orders -> Order Details -> Products -> Categories
```

`Order Details` contains the line quantity, unit price, discount, and product reference. The `Orders` header provides the customer, employee, and transaction date. Northwind employee attribution is direct:

```text
Orders.EmployeeID -> Employees.EmployeeID
```

Task 1 inspects both SQLite schemas programmatically, including their tables, columns, datatypes, keys, relationships, and record counts. The inspected SQLite metadata remains the source of truth for source-schema documentation.

## Assignment Deliverables

### Task 1 : Data Understanding & Source-to-Target Mapping

#### Exploratory Data Analysis (EDA)

The [EDA notebook](notebooks/dsi310_northwind_chinook_eda_v1_0.ipynb) downloads and connects to both SQLite databases, then generates metadata inventories and visual summaries. It examines:

- business tables and columns
- source datatypes
- record counts and data volume
- primary keys and foreign-key relationships
- common business entities
- common sales processes and source-specific differences

The two source visuals are documented as **Database Schema Diagrams (Task 1 class-diagram output)**. They show source tables, columns, datatypes, primary keys, foreign keys, and table relationships. DBML definitions are generated from inspected metadata, while dbdiagram.io is used only to render and arrange the final diagrams.

#### Database Schema Diagrams (Task 1 Class-Diagram Output)

<table>
  <tr>
    <th>Chinook</th>
    <th>Northwind</th>
  </tr>
  <tr>
    <td>
      <a href="docs/task1/diagrams/chinook_database_schema.png">
        <img src="docs/task1/diagrams/chinook_database_schema.png" width="100%">
      </a>
    </td>
    <td>
      <a href="docs/task1/diagrams/northwind_database_schema.png">
        <img src="docs/task1/diagrams/northwind_database_schema.png" width="100%">
      </a>
    </td>
  </tr>
</table>

- [Chinook source DBML](docs/task1/chinook.dbml)
- [Northwind source DBML](docs/task1/northwind.dbml)

#### Source-to-Target Mapping

The mapping integrates source fields into `DimCustomer`, `DimEmployee`, `DimProduct`, `DimTime`, `DimSourceSystem`, and `FactSales`. Important transformations include:

- Chinook integer customer IDs and Northwind text customer IDs become source-prefixed canonical `TEXT` identifiers such as `CHINOOK:<id>` and `NORTHWIND:<id>`.
- Chinook `Track` and Northwind `Products` both map to `DimProduct`.
- Chinook music classification maps to `GenreName`; Northwind product classification maps to `CategoryName`.
- Attributes that a source cannot provide remain `NULL` rather than receiving fabricated values.
- Source-specific joins preserve the different customer, employee, product, date, and transaction structures.

The complete mapping is available as an [Excel workbook](docs/task1/source_to_target_mapping.xlsx) and [CSV file](docs/task1/source_to_target_mapping.csv).

### Task 2 : Dimensional Modeling & Schema Design

The warehouse uses a unified Kimball Star Schema with `FactSales` at the center and five directly related, conformed dimensions. The declared grain is:

> One row per sales transaction line item.

This means one Chinook `InvoiceLine` row or one Northwind `Order Details` row becomes one fact row.

`FactSales` contains exactly seven columns:

| Column | Role |
| --- | --- |
| `DateKey` | Foreign key to `DimTime` |
| `CustomerID` | Source-prefixed customer foreign key |
| `EmployeeID` | Nullable source-prefixed employee foreign key |
| `ProductID` | Source-prefixed product foreign key |
| `SourceSystemID` | Foreign key identifying Chinook or Northwind |
| `SalesQuantity` | Additive measure copied from source `Quantity` |
| `SalesAmount` | Additive measure calculated as `UnitPrice * Quantity` |

Northwind `Discount` is intentionally not included in the assignment-defined `SalesAmount`. Applying it to only one source would give the unified measure inconsistent meanings.

The dimensions are `DimCustomer`, `DimEmployee`, `DimProduct`, `DimTime`, and `DimSourceSystem`. `DimTime` uses an integer `DateKey` in `YYYYMMDD` form and supplies shared calendar attributes for both businesses.

A star schema was selected because each dimension relates directly to `FactSales`, reducing join complexity for BI queries. The conformed dimensions provide shared analytical views across the two businesses while the single line-item grain preserves product-level detail.

Detailed Task 2 artifacts:

- [Dimensional model specification](docs/task2/DIMENSIONAL_MODEL.md)
- [Dimensional modeling workbook (assignment template)](docs/task2/data_lake_design.xlsx)
- [Unified star-schema DBML](docs/task2/unified_star_schema.dbml)
- [Unified star-schema SVG](docs/task2/diagrams/unified_star_schema.svg)

#### Unified Star Schema

![Unified Kimball Star Schema](docs/task2/diagrams/unified_star_schema.png)

`FactSales` is the central fact table. Each dimension connects directly to it, and `DimEmployee.ReportsTo` preserves the employee hierarchy through a self-reference.

### Task 3 : Data Expression & Business Value

#### Fact Table Row Expression

The accepted example begins with Northwind order `10248`, product `11`, customer `VINET` (Paul Henriot), employee `5` (Steven Buchanan), transaction date `2016-07-04`, and product Queso Cabrales. The source line has quantity `12` and unit price `14.00`, producing `SalesAmount = 168.00`.

Its warehouse representation is:

| FactSales column | Value |
| --- | --- |
| `DateKey` | `20160704` |
| `CustomerID` | `NORTHWIND:VINET` |
| `EmployeeID` | `NORTHWIND:5` |
| `ProductID` | `NORTHWIND:11` |
| `SourceSystemID` | `2` |
| `SalesQuantity` | `12` |
| `SalesAmount` | `168.00` |

> On July 4, 2016, one Northwind sales line item recorded customer Paul Henriot purchasing 12 units of Queso Cabrales for a SalesAmount of 168.00, with the order attributed directly to Sales Manager Steven Buchanan.

See the complete [Fact Table Row Expression](docs/task3/FACT_ROW_INTERPRETATION.md) for its source fields, dimension context, and interpretation notes.

#### Report Mock-up (BI Dashboard)

Task 3.2 is delivered as an interactive Streamlit dashboard (`app.py`) rather than a static mock-up. It answers the business questions from the [dimensional model's BI coverage section](docs/task2/DIMENSIONAL_MODEL.md) across five tabs:

- **Revenue by Source System** — `SUM(FactSales.SalesAmount)` grouped by `DimSourceSystem.SourceSystemName`, with a validation badge confirming the computed totals reproduce the documented figures (Chinook 2,328.60 vs. Northwind 448,475,298.72), plus a normalized **Average SalesAmount per Line Item** comparison (Chinook ≈ 1.04 vs. Northwind ≈ 736.07) since the raw totals are dominated by the ~272x difference in transaction volume (2,240 vs. 609,283 line items) rather than reflecting comparable business performance.
- **Top Customers** — top 10 by spend, optionally split by source system.
- **Top Products** — top 10 by spend/quantity, showing Chinook `GenreName` and Northwind `CategoryName` side by side.
- **Employee Performance** — grouped by employee, with a persistent note on the Chinook support-representative attribution caveat.
- **Analysis by Date** — revenue/quantity by day, month, quarter, or year, optionally split by source system for the same Chinook-vs-Northwind comparison.

An expander above the tabs also surfaces the Task 3.1 fact-row interpretation interactively, letting a viewer pick any `FactSales` row and see its generated business sentence, not just the one documented example.

The dashboard's recurring categories are color-coded consistently on a white background: **Chinook = yellow (`#eecf8c`)**, **Northwind = blue (`#5388d4`)**, **Combined = teal (`#0d9488`)**.

<table>
  <tr>
    <td>
      <img src="docs/task3/streamlit_revenue_comparison.png" width="100%">
      <p><em>Business takeaway: Northwind (food &amp; beverage) accounts for virtually all of OmniCorp's combined revenue in the current dataset, while Chinook (music) contributes a negligible share. This reflects each business's transaction volume in the source data (609,283 vs. 2,240 line items) — it is not evidence that one business model is inherently more profitable per sale. The bar chart shows the true-to-scale gap; the log-scale dot chart below it keeps both businesses visibly plotted on the same chart for comparison.</em></p>
    </td>
  </tr>
  <tr>
    <td>
      <img src="docs/task3/streamlit_avg_line_item.png" width="100%">
      <p><em>Business takeaway: a typical Northwind sale (≈$736 per line item) is far larger than a typical Chinook sale (≈$1.04 per line item), because Northwind orders are bulk food/beverage purchases (multiple units per line) while Chinook sales are single-track music purchases. Normalizing by line item — rather than looking at raw totals — is what actually lets a business analyst compare "how big is a typical sale" between the two acquired businesses.</em></p>
    </td>
  </tr>
</table>

See [Running the Streamlit App](#running-the-streamlit-app) below to launch it. The original static documentation — [Fact Table Row Expression](docs/task3/FACT_ROW_INTERPRETATION.md) and [Report Mock-up documentation](docs/task3/BI_DASHBOARD_MOCKUP.md) — remains as the source-to-warehouse traceability reference the app's validation check is built against.

### Task 4 : Critical Thinking & Data Engineering Challenges

#### Data Ingestion & Integration

The main integration challenges are datatype differences, source-local identifier collisions, structural and naming differences, missing attributes, employee-attribution semantics, consistent measures, data-quality validation, and provenance. For example, Chinook `Customer.CustomerId` is `INTEGER`, while Northwind `Customers.CustomerID` is `TEXT`; both are normalized to target `TEXT` and prefixed by source. `DimSourceSystem` preserves the business origin of each fact.

#### Schema Evolution

If a third acquisition records the same sales process at the same line-item grain, its data should extend the existing `FactSales` and conformed dimensions through a new Source-to-Target Mapping. A conceptual source member `3 = ThirdCompany` and namespace `THIRDCOMPANY:<source id>` would preserve provenance and key uniqueness. A different business process or grain may require a separate fact table instead. This is an evolution strategy, not a claim that a third company currently exists.

#### Data Lake vs. Data Warehouse

A Data Lake provides flexible raw or source-aligned retention for ingestion, exploration, lineage, and reprocessing. The Data Warehouse publishes curated, standardized facts and dimensions for repeatable BI and governed metrics.

```text
Source Systems -> Data Lake / source-aligned storage -> validation + standardization + semantic mapping -> Data Warehouse -> BI / reporting
```

The current repository designs the warehouse analytical layer and its mappings, not a production Data Lake. See the [complete Task 4 discussion](docs/task4/TASK4_CRITICAL_THINKING.md) for details.

## Key Design Decisions

| Decision | Design |
| --- | --- |
| Identifier strategy | Source-prefixed canonical `TEXT` IDs: `CHINOOK:<id>` and `NORTHWIND:<id>` |
| Missing attributes | Preserve unavailable source attributes as `NULL` rather than inventing values |
| Employee attribution | Northwind uses direct order attribution; Chinook uses the customer's assigned support representative |
| Source provenance | Every fact references `DimSourceSystem` so Chinook and Northwind remain distinguishable |
| Measure consistency | `SalesAmount = UnitPrice * Quantity`; Northwind `Discount` is excluded from the assignment-defined measure |

## Repository Structure

```text
Data-Warehouse-DSI310/
├── README.md
├── requirements.txt
├── app.py
├── app/
│   ├── __init__.py
│   ├── data_loader.py
│   ├── model.py
│   ├── queries.py
│   └── validation.py
├── notebooks/
│   ├── dsi310_northwind_chinook_eda_v1_0.ipynb
│   └── original/
│       └── dsi310_northwind_chinook_eda_v1_0 (original).ipynb
└── docs/
    ├── task1/
    │   ├── chinook.dbml
    │   ├── northwind.dbml
    │   ├── source_to_target_mapping.csv
    │   ├── source_to_target_mapping.xlsx
    │   └── diagrams/
    │       ├── chinook_database_schema.png
    │       ├── chinook_database_schema.svg
    │       ├── northwind_database_schema.png
    │       └── northwind_database_schema.svg
    ├── task2/
    │   ├── DIMENSIONAL_MODEL.md
    │   ├── data_lake_design.xlsx
    │   ├── unified_star_schema.dbml
    │   └── diagrams/
    │       ├── unified_star_schema.png
    │       └── unified_star_schema.svg
    ├── task3/
    │   ├── FACT_ROW_INTERPRETATION.md
    │   ├── BI_DASHBOARD_MOCKUP.md
    │   ├── bi_revenue_comparison_mockup.png
    │   ├── streamlit_revenue_comparison.png
    │   └── streamlit_avg_line_item.png
    └── task4/
        └── TASK4_CRITICAL_THINKING.md
```

## Running the EDA Notebook

Create and activate a repository-local virtual environment, then install the declared dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Open `notebooks/dsi310_northwind_chinook_eda_v1_0.ipynb` in VS Code or a Jupyter interface and run the cells in order. The notebook downloads the source SQLite files into `notebooks/data/` when needed. That directory is excluded from Git.

## Running the Streamlit App

With the same virtual environment active and dependencies installed (see above), run:

```powershell
streamlit run app.py
```

The app downloads the same Chinook and Northwind SQLite files used by the EDA notebook into `notebooks/data/` on first run (skipped if already present) and builds the unified `FactSales` fact table and its five conformed dimensions in memory. See [Report Mock-up (BI Dashboard)](#report-mock-up-bi-dashboard) above for what the dashboard shows. The validation check behind its Revenue-tab badge can also be run standalone with `python -m app.validation`.

## Project Scope and Limitations

- This repository is a dimensional-modeling and analytical-design assignment; it does not deploy a production warehouse, ETL pipeline, or Data Lake platform.
- The source SQLite databases remain the source of truth for inspected source tables, columns, datatypes, primary keys, and foreign keys.
- Northwind `Discount` is intentionally excluded from the assignment-defined `SalesAmount`.
- Chinook employee attribution represents the customer's assigned support representative rather than a salesperson recorded on an invoice.
- The Task 3 report uses the provided datasets as inspected. Its results should not be treated as normalized real-company performance or as a currency comparison.
