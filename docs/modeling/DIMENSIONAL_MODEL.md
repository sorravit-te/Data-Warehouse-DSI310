# Unified Kimball Dimensional Model Contract

## 1. Purpose and scope

This document defines the logical Kimball dimensional-model contract for the unified Chinook and Northwind data warehouse. It is limited to Task 2.1: defining the fact grain, target tables, logical datatypes, key strategy, relationships, measures, source interpretations, and business-intelligence coverage before a visual model or physical implementation is created.

The accepted Task 1.2 source-to-target mapping is the source of truth for the decisions in this contract. The inspected SQLite schemas remain the source of truth for source tables, columns, datatypes, primary keys, and foreign keys.

This task does not implement ETL, create a physical warehouse database, modify either source database, or define Task 3 or Task 4 deliverables. The target datatypes below are logical warehouse types; database-specific syntax, precision, constraints, and physical implementation details remain to be finalized later.

## 2. Star-schema contract

`FactSales` is the central fact table. Each of the five dimensions connects directly to it.

| Dimension           | FactSales foreign key | Dimension primary key              | Cardinality                         |
| ------------------- | --------------------- | ---------------------------------- | ----------------------------------- |
| `DimTime`         | `DateKey`           | `DimTime.DateKey`                | One dimension row to many fact rows |
| `DimCustomer`     | `CustomerID`        | `DimCustomer.CustomerID`         | One dimension row to many fact rows |
| `DimEmployee`     | `EmployeeID`        | `DimEmployee.EmployeeID`         | One dimension row to many fact rows |
| `DimProduct`      | `ProductID`         | `DimProduct.ProductID`           | One dimension row to many fact rows |
| `DimSourceSystem` | `SourceSystemID`    | `DimSourceSystem.SourceSystemID` | One dimension row to many fact rows |

The model remains a star schema. Category, Genre, Artist, Album, Supplier, Geography, and other source entities are not introduced as separate dimensions for this assignment. Relevant category and genre labels are flattened into `DimProduct`; relevant customer and employee geography attributes remain in their respective dimensions.

A star schema is appropriate for the assignment's BI and reporting use cases because `FactSales` is the central analytical fact table and each business dimension joins directly to it. This reduces query join complexity and makes common aggregations, including revenue by customer, product, employee, date, and source system, straightforward. Conformed dimensions provide a consistent analytical view across Chinook and Northwind while preserving the required line-item `FactSales` grain.

## 3. FactSales grain

The declared grain is:

> One row per sales transaction line item.

The source interpretation is:

- Chinook: one row per `InvoiceLine` row.
- Northwind: one row per `Order Details` row.

Line-item grain preserves the lowest common sales detail needed by this assignment. Each fact row identifies the product sold, the customer, the applicable employee interpretation, the transaction date, and the originating source system. This supports product-level, customer-level, employee-level, date-level, and source-system analysis without allocating header-level totals or losing product detail.

No separate `FactSales` surrogate key is defined. The assignment does not require one, and the fact contract contains only the seven attributes listed below.

## 4. FactSales

| Column             | Logical type                         | Role and definition                                                                                                                                                                                                               |
| ------------------ | ------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DateKey`        | `INTEGER`                          | Foreign key to`DimTime.DateKey`; derived in `YYYYMMDD` format from `Invoice.InvoiceDate` or `Orders.OrderDate`. Missing source dates require an explicit later ETL decision and must not be fabricated.                   |
| `CustomerID`     | `TEXT`                             | Foreign key to`DimCustomer.CustomerID`; uses the source-prefixed canonical customer identifier. Northwind orders without a customer retain `NULL`.                                                                            |
| `EmployeeID`     | `TEXT`, nullable                   | Foreign key to`DimEmployee.EmployeeID`; uses the source-prefixed canonical employee identifier. It is nullable because the source employee relationship can be absent and because Chinook derives this relationship indirectly. |
| `ProductID`      | `TEXT`                             | Foreign key to`DimProduct.ProductID`; uses the source-prefixed canonical product identifier. Both line-item sources require a product reference.                                                                                |
| `SourceSystemID` | `INTEGER`                          | Foreign key to`DimSourceSystem.SourceSystemID`; `1` for Chinook and `2` for Northwind.                                                                                                                                      |
| `SalesQuantity`  | `INTEGER`                          | Additive measure copied from the source line`Quantity`.                                                                                                                                                                         |
| `SalesAmount`    | `NUMERIC` / `DECIMAL`-compatible | Additive measure calculated as source line`UnitPrice * Quantity`.                                                                                                                                                               |

### 4.1 Source interpretation

| Fact attribute     | Chinook                                                                                | Northwind                                                                            |
| ------------------ | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `DateKey`        | `InvoiceLine.InvoiceId -> Invoice.InvoiceId -> Invoice.InvoiceDate`                  | `Order Details.OrderID -> Orders.OrderID -> Orders.OrderDate`                      |
| `CustomerID`     | `InvoiceLine.InvoiceId -> Invoice.CustomerId`, then the Chinook customer prefix      | `Order Details.OrderID -> Orders.CustomerID`, then the Northwind customer prefix   |
| `EmployeeID`     | `InvoiceLine -> Invoice -> Customer -> Customer.SupportRepId -> Employee.EmployeeId` | `Order Details -> Orders.EmployeeID -> Employees.EmployeeID`                       |
| `ProductID`      | `InvoiceLine.TrackId -> Track.TrackId`, then the Chinook product prefix              | `Order Details.ProductID -> Products.ProductID`, then the Northwind product prefix |
| `SourceSystemID` | Constant`1`                                                                          | Constant`2`                                                                        |
| `SalesQuantity`  | `InvoiceLine.Quantity`                                                               | `Order Details.Quantity`                                                           |
| `SalesAmount`    | `InvoiceLine.UnitPrice * InvoiceLine.Quantity`                                       | `Order Details.UnitPrice * Order Details.Quantity`                                 |

### 4.2 Measures and Discount handling

`SalesQuantity` equals the source line `Quantity`.

`SalesAmount` equals the source line `UnitPrice * Quantity`.

Northwind `Order Details.Discount` is not applied to `SalesAmount`. A separate discount-adjusted or net-sales measure may be considered in later dimensional-modeling work, but it is not part of the assignment-defined `SalesAmount` and is not added to this contract.

### 4.3 Employee semantics

For Chinook, `FactSales.EmployeeID` is derived indirectly through:

`Invoice -> Customer -> Customer.SupportRepId -> Employee.EmployeeId`

This employee is the customer's assigned support representative. It is not an employee explicitly recorded on the Chinook invoice or sales line. Analyses described as Chinook employee performance must therefore be interpreted as sales associated with each customer's assigned support representative, not direct sales attribution.

For Northwind, `FactSales.EmployeeID` is derived directly from `Orders.EmployeeID`. Because either source relationship can be absent, `FactSales.EmployeeID` is nullable.

## 5. DimCustomer

| Column           | Logical type          | Contract                                                                                                  |
| ---------------- | --------------------- | --------------------------------------------------------------------------------------------------------- |
| `CustomerID`   | `TEXT`, primary key | Source-prefixed canonical customer identifier.                                                            |
| `CustomerName` | `TEXT`              | Chinook uses trimmed`Customer.FirstName + Customer.LastName`; Northwind uses `Customers.ContactName`. |
| `CompanyName`  | `TEXT`, nullable    | `Customer.Company` or `Customers.CompanyName`.                                                        |
| `City`         | `TEXT`, nullable    | `Customer.City` or `Customers.City`.                                                                  |
| `State`        | `TEXT`, nullable    | `Customer.State` or standardized `Customers.Region`.                                                  |
| `Country`      | `TEXT`, nullable    | `Customer.Country` or `Customers.Country`.                                                            |
| `PostalCode`   | `TEXT`, nullable    | `Customer.PostalCode` or `Customers.PostalCode`.                                                      |
| `Phone`        | `TEXT`, nullable    | `Customer.Phone` or `Customers.Phone`.                                                                |
| `Email`        | `TEXT`, nullable    | `Customer.Email` for Chinook; `NULL` for Northwind because `Customers` has no email column.         |

The canonical key strategy is:

- Chinook: `CHINOOK:<Customer.CustomerId>`
- Northwind: `NORTHWIND:<Customers.CustomerID>`

The source prefix prevents cross-source identifier collisions. It also normalizes the source datatype difference between Chinook's `INTEGER` `CustomerId` and Northwind's `TEXT` `CustomerID` into one warehouse `TEXT` key.

## 6. DimEmployee

| Column           | Logical type          | Contract                                                                            |
| ---------------- | --------------------- | ----------------------------------------------------------------------------------- |
| `EmployeeID`   | `TEXT`, primary key | Source-prefixed canonical employee identifier.                                      |
| `EmployeeName` | `TEXT`              | Trimmed source`FirstName + LastName`.                                             |
| `Title`        | `TEXT`, nullable    | `Employee.Title` or `Employees.Title`.                                          |
| `City`         | `TEXT`, nullable    | `Employee.City` or `Employees.City`.                                            |
| `Country`      | `TEXT`, nullable    | `Employee.Country` or `Employees.Country`.                                      |
| `ReportsTo`    | `TEXT`, nullable    | Source manager identifier converted to the same source-prefixed employee namespace. |

The canonical key strategy is:

- Chinook: `CHINOOK:<Employee.EmployeeId>`
- Northwind: `NORTHWIND:<Employees.EmployeeID>`

`ReportsTo` preserves the employee hierarchy within the originating source namespace:

- Chinook: `CHINOOK:<Employee.ReportsTo>` when present.
- Northwind: `NORTHWIND:<Employees.ReportsTo>` when present.

The hierarchy remains an attribute-level self-reference within `DimEmployee`; it does not create another dimension or snowflake the model.

## 7. DimProduct

| Column           | Logical type          | Contract                                                                                                                                                  |
| ---------------- | --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ProductID`    | `TEXT`, primary key | Source-prefixed canonical product identifier.                                                                                                             |
| `ProductName`  | `TEXT`              | `Track.Name` for Chinook or `Products.ProductName` for Northwind.                                                                                     |
| `CategoryName` | `TEXT`, nullable    | `NULL` for Chinook; `Categories.CategoryName` for Northwind through `Products.CategoryID`.                                                          |
| `GenreName`    | `TEXT`, nullable    | `Genre.Name` for Chinook through `Track.GenreId`; `NULL` for Northwind.                                                                             |
| `Composer`     | `TEXT`, nullable    | `Track.Composer` for Chinook; `NULL` for Northwind.                                                                                                   |
| `UnitPrice`    | `NUMERIC`, nullable | `Track.UnitPrice` or `Products.UnitPrice`. This descriptive dimension value does not replace the source line price used by `FactSales.SalesAmount`. |

The canonical key strategy is:

- Chinook: `CHINOOK:<Track.TrackId>`
- Northwind: `NORTHWIND:<Products.ProductID>`

For Chinook, a product is a `Track`. `GenreName` comes from `Genre`, `CategoryName` is `NULL`, and `Composer` comes from `Track.Composer`.

For Northwind, a product is a `Products` row. `CategoryName` comes from `Categories.CategoryName`, while `GenreName` and `Composer` are `NULL`.

Album and Artist are not treated as Category, and Supplier is not treated as Genre. Missing cross-source concepts remain `NULL` rather than being forced into unrelated semantics.

## 8. DimTime

| Column         | Logical type             | Contract                                                                    |
| -------------- | ------------------------ | --------------------------------------------------------------------------- |
| `DateKey`    | `INTEGER`, primary key | Calendar date key in`YYYYMMDD` format.                                    |
| `FullDate`   | `DATE`                 | Calendar date derived from the source transaction datetime.                 |
| `DayOfMonth` | `INTEGER`              | Calendar day number derived from`FullDate`.                               |
| `DayOfWeek`  | `TEXT`                 | Documented day-of-week label derived from`FullDate`.                      |
| `Month`      | `INTEGER`              | Calendar month number derived from`FullDate`.                             |
| `Quarter`    | `INTEGER`              | Calendar quarter number from`1` through `4`, derived from `FullDate`. |
| `Year`       | `INTEGER`              | Calendar year derived from`FullDate`.                                     |

The contributing source dates are `Invoice.InvoiceDate` for Chinook and `Orders.OrderDate` for Northwind.

`DimTime` is one conformed calendar dimension shared by both source systems. It contains one row per unique calendar date, not one row per transaction. Source datetimes are reduced to their calendar-date component before the key and attributes are derived.

## 9. DimSourceSystem

| Column               | Logical type             | Contract                           |
| -------------------- | ------------------------ | ---------------------------------- |
| `SourceSystemID`   | `INTEGER`, primary key | Static source-system identifier.   |
| `SourceSystemName` | `TEXT`                 | Human-readable source-system name. |

The static members are:

| SourceSystemID | SourceSystemName |
| -------------: | ---------------- |
|          `1` | Chinook          |
|          `2` | Northwind        |

This dimension identifies the business origin of each fact row and allows BI users to compare performance across the acquired source systems.

## 10. BI requirement coverage

| Assignment question             | FactSales measure or calculation                                            | Dimensions used                                 | Intended analysis                                                                                                                                       |
| ------------------------------- | --------------------------------------------------------------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Revenue: music vs food/beverage | `SUM(FactSales.SalesAmount)`                                              | `DimSourceSystem`                             | Group by`DimSourceSystem.SourceSystemName`; Chinook represents music and Northwind represents food/beverage and other product sales.                  |
| Top 10 customers                | `SUM(FactSales.SalesAmount)`; optionally `SUM(FactSales.SalesQuantity)` | `DimCustomer`, optionally `DimSourceSystem` | Group by canonical customer and name, sort revenue descending, and return the top 10. The source dimension can separate or compare businesses.          |
| Top products / tracks           | `SUM(FactSales.SalesAmount)` and `SUM(FactSales.SalesQuantity)`         | `DimProduct`, optionally `DimSourceSystem`  | Group by canonical product and product name; use genre for Chinook or category for Northwind where available.                                           |
| Employee performance            | `SUM(FactSales.SalesAmount)` and, optionally, `SUM(FactSales.SalesQuantity)` | `DimEmployee.EmployeeID`, `DimEmployee.EmployeeName`, and `DimEmployee.Title`; optionally `DimSourceSystem.SourceSystemName` | Group by employee ID and name, with optional analysis by title. For Chinook, `FactSales.EmployeeID` comes from `Customer.SupportRepId`, so results represent sales associated with each customer's assigned support representative, not an employee explicitly recorded as the salesperson on the invoice. For Northwind, `FactSales.EmployeeID` comes from `Orders.EmployeeID` and represents direct order employee attribution. `DimEmployee.Title` supports analysis by employee title, including Chinook support-agent roles where present in the source data. |
| Analysis by date                | `SUM(FactSales.SalesAmount)` and `SUM(FactSales.SalesQuantity)`         | `DimTime`                                     | Group or filter by full date, day, month, quarter, or year.                                                                                             |
| Analysis by source system       | `SUM(FactSales.SalesAmount)` and `SUM(FactSales.SalesQuantity)`         | `DimSourceSystem`                             | Compare revenue and quantity between Chinook and Northwind.                                                                                             |

## 11. Design decisions and assumptions

| Decision                    | Contract                                                                                                                                                                                |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Canonical identifiers       | Customer, employee, product, and employee-manager identifiers use`CHINOOK:` or `NORTHWIND:` prefixes to prevent cross-source collisions and standardize differing source key types. |
| Missing attributes          | Use`NULL` when a source attribute or optional relationship is unavailable. Do not fabricate values.                                                                                   |
| Fact grain                  | `FactSales` contains one row per sales transaction line item: one `InvoiceLine` or one `Order Details` row.                                                                       |
| Sales amount                | `SalesAmount` is the source line `UnitPrice * Quantity`.                                                                                                                            |
| Northwind Discount          | `Order Details.Discount` is not applied to assignment-defined `SalesAmount`. A separate net-sales measure may be considered later.                                                  |
| Chinook employee limitation | Chinook identifies the customer's assigned support representative through`Customer.SupportRepId`; it does not record an employee directly on the invoice or sales line.               |
| Logical datatypes           | The documented types are proposed logical warehouse types. Physical database syntax, precision, and constraints are outside Task 2.1.                                                   |
| Schema form                 | The five dimensions connect directly to`FactSales`. No separate category, genre, artist, album, supplier, geography, or other snowflaked dimension is introduced.                     |
| Implementation boundary     | Task 2.1 defines and documents the model contract only. It does not implement ETL or create a physical warehouse database.                                                              |
