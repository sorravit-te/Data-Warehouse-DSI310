# Task 4 — Critical Thinking & Data Engineering Challenges

## 4.1 Data Ingestion & Integration

Chinook and Northwind both record sales, but their independent schemas use different names,
structures, datatypes, and business meanings. Integration must standardize these differences while
preserving the `FactSales` grain: one row per sales transaction line item.

| Challenge | Example | Handling |
| --- | --- | --- |
| Datatype differences | Chinook `Customer.CustomerId` is `INTEGER`, while Northwind `Customers.CustomerID` is `TEXT`. | Convert both to target `TEXT` identifiers and apply the same transformation in dimensions and fact foreign keys. |
| Primary-key collisions | Identical native customer, employee, or product IDs from the two systems do not identify the same entity. | Use source-prefixed canonical IDs such as `CHINOOK:<id>` and `NORTHWIND:<id>`. |
| Naming and structural differences | `InvoiceLine` and `Order Details` feed `FactSales`; `Track` and `Products` feed `DimProduct`. | Use an explicit Source-to-Target Mapping with source-specific joins and transformations rather than simple renaming. |
| Missing or asymmetric attributes | Northwind has no customer `Email`; Chinook supplies `GenreName` and `Composer`; Northwind supplies `CategoryName`. | Store unavailable target attributes as `NULL` and do not invent values. |
| Employee attribution | Northwind uses `Orders.EmployeeID` directly; Chinook reaches `Employee` through `Customer.SupportRepId`. | Treat Northwind as direct order attribution and Chinook as the customer's assigned support representative; compare employee results with this semantic difference in mind. |
| Measure consistency | Both sources provide line `UnitPrice` and `Quantity`; Northwind also provides `Discount`. | Populate `SalesQuantity` from `Quantity` and calculate `SalesAmount = UnitPrice * Quantity` for both sources. Northwind `Discount` remains excluded from this assignment's `SalesAmount`. |
| Date and data quality | `Invoice.InvoiceDate` and `Orders.OrderDate` supply the transaction date. Keys, references, lines, dates, quantities, and prices may also fail validation. | Map valid dates to shared `DimTime`, derive `DateKey = YYYYMMDD`, and validate keys, references, duplicate lines, NULLs, dates, and type conversion before loading. |
| Provenance and scale | `DimSourceSystem` identifies Chinook or Northwind. The sources contain 2,240 `InvoiceLine` rows and 609,283 `Order Details` rows. | Populate `SourceSystemID` on every fact, retain lineage, and size ingestion work appropriately without treating volume as business performance. |

The canonical transformation must be identical wherever an identifier appears. For example, a
`CHINOOK:59` customer key in `DimCustomer` must be represented as `CHINOOK:59` in the related
`FactSales.CustomerID`; the same rule applies to employee and product keys.

Validation should confirm source-line uniqueness, required references, parseable transaction dates,
and usable `Quantity` and `UnitPrice` values. Invalid records should be logged and handled explicitly
rather than loaded with fabricated dates, identifiers, measures, or descriptive attributes.

Different source volumes may justify different operational batch sizes or schedules in a production
pipeline, but both ingestion paths must preserve the same keys, fact grain, measures, and quality rules.

## 4.2 Schema Evolution

If OmniCorp acquires a third company, the first decision is whether its sales data represents the same
business process at the same line-item grain. If it does, reuse `FactSales` and the existing conformed
dimensions. If the source represents a different process or grain, a separate fact table may be more
appropriate.

| Change | Evolution approach | Reason |
| --- | --- | --- |
| New source system | Add the conceptual member `3 = ThirdCompany` to `DimSourceSystem`. | Existing `FactSales.SourceSystemID` can identify the new business without changing the fact structure. |
| New source identifiers | Extend the namespace with `THIRDCOMPANY:<source id>`. | The prefix prevents collisions while preserving traceability to the source. |
| Different source names or joins | Create a new Source-to-Target Mapping. | Source-specific structures should be transformed into the accepted warehouse concepts. |
| Compatible customers, employees, products, and dates | Reuse `DimCustomer`, `DimEmployee`, `DimProduct`, and `DimTime` when their meanings conform. | Shared dimensions support cross-business analysis and avoid source-specific copies of the same concept. |
| Missing or new attributes | Use `NULL` when an attribute is unavailable; add a nullable dimension attribute only when it has clear analytical value. | This preserves source truth and prevents unnecessary sparse columns. |
| Different business process or grain | Consider a separate fact table that can share conformed dimensions. | A non-sales process, such as an inventory snapshot, should not be forced into line-item `FactSales`. |

A compatible third source should therefore extend mappings rather than create separate customer
dimensions or sales fact tables for each company. It must follow the existing contracts for identifiers,
`SalesQuantity`, `SalesAmount`, dates, NULL handling, and employee meaning.

Schema evolution should be additive. Existing `CHINOOK:<id>` and `NORTHWIND:<id>` values must remain
stable, historical Chinook and Northwind facts must not be rewritten, and the meanings of existing
columns must not change when the third source is added.

This approach makes the star schema flexible: conformed dimensions can accept compatible members from
new sources, while a genuinely different event can use another fact table without weakening the declared
grain of `FactSales`.

## 4.3 Data Lake vs. Data Warehouse

A Data Lake and a Data Warehouse serve complementary roles. The lake retains flexible raw or
source-aligned data, while the warehouse publishes curated structures with consistent analytical meaning.

| Aspect | Data Lake | Data Warehouse |
| --- | --- | --- |
| Purpose | Preserve data for ingestion, exploration, lineage, and reprocessing. | Deliver consistent data for analytics, dashboards, and reporting. |
| Data form | Raw or source-aligned structured, semi-structured, and unstructured data. | Curated and standardized facts and dimensions. |
| Schema and transformation | Structure may be applied during use or transformation, often described as schema-on-read. | Business rules and target structures are applied before BI publication, often described as schema-on-write. |
| Typical use | Source investigation, profiling, new mappings, and onboarding acquisitions. | Repeatable queries and governed metrics for business analysts. |
| Role at OmniCorp | Retain Chinook, Northwind, and future source data in source-aligned form. | Publish the conformed star schema built from `FactSales`, `DimCustomer`, `DimEmployee`, `DimProduct`, `DimTime`, and `DimSourceSystem`. |

The conceptual flow is:

```text
Source systems
    -> Data Lake / raw or source-aligned storage
    -> validation + standardization + semantic mapping
    -> Data Warehouse / conformed star schema
    -> BI / reporting
```

The lake preserves original values and source-specific fields so transformations can be checked or rerun.
For example, Northwind `Discount` may remain available in source-aligned data even though the current
warehouse deliberately excludes it from `SalesAmount`.

The warehouse provides the simpler analytical interface. Its line-item `FactSales` grain, shared
dimensions, canonical identifiers, and consistent measures allow BI users to calculate metrics such as
`SUM(FactSales.SalesAmount)` without recreating the Chinook and Northwind source joins.

Both layers still require concise governance for ownership, access, metadata, quality, retention, and
lineage. The current DSI310 project designs the warehouse analytical layer and its mappings; it does not
implement a production Data Lake or a complete production warehouse platform.

OmniCorp can use a Data Lake for flexible raw or source-aligned retention and a Data Warehouse for
curated, conformed BI.
