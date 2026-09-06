# Task 3.1 — Fact Table Row Expression

## Selected Source Transaction

The selected transaction is exactly one Northwind `Order Details` row, identified by the composite source key `(OrderID 10248, ProductID 11)`. Its order, customer, employee, product, and category values were resolved from the current Northwind SQLite database.

| Source Field | Value |
| --- | --- |
| `Order Details.OrderID` | `10248` |
| `Order Details.ProductID` | `11` |
| `Orders.CustomerID` | `VINET` |
| `Orders.EmployeeID` | `5` |
| `Orders.OrderDate` | `2016-07-04` |
| `Order Details.UnitPrice` | `14.00` |
| `Order Details.Quantity` | `12` |
| `Order Details.Discount` | `0.0` — source value only; not applied to `SalesAmount` |

## Derived FactSales Row

| FactSales Column | Value |
| --- | --- |
| `DateKey` | `20160704` |
| `CustomerID` | `NORTHWIND:VINET` |
| `EmployeeID` | `NORTHWIND:5` |
| `ProductID` | `NORTHWIND:11` |
| `SourceSystemID` | `2` |
| `SalesQuantity` | `12` |
| `SalesAmount` | `168.00` |

`SalesAmount = UnitPrice × Quantity = 14.00 × 12 = 168.00`

## Dimension Context

| Dimension | Key | Business Value |
| --- | --- | --- |
| `DimTime` | `20160704` | Full date: 2016-07-04 |
| `DimCustomer` | `NORTHWIND:VINET` | Paul Henriot |
| `DimEmployee` | `NORTHWIND:5` | Steven Buchanan — Sales Manager |
| `DimProduct` | `NORTHWIND:11` | Queso Cabrales — Dairy Products |
| `DimSourceSystem` | `2` | Northwind |

## Business Interpretation

On July 4, 2016, one Northwind sales line item recorded customer Paul Henriot purchasing 12 units of Queso Cabrales for a SalesAmount of 168.00, with the order attributed directly to Sales Manager Steven Buchanan.

## Dimension References

The sentence references all five dimensions:

- `DimTime`: July 4, 2016
- `DimCustomer`: Paul Henriot
- `DimEmployee`: Steven Buchanan, Sales Manager
- `DimProduct`: Queso Cabrales
- `DimSourceSystem`: Northwind

## Interpretation Notes

- `FactSales` grain is one sales transaction line item.
- Northwind employee attribution comes directly from `Orders.EmployeeID`.
- `SalesAmount` is `UnitPrice × Quantity`.
- Northwind `Discount` is intentionally excluded from the assignment-defined `SalesAmount`.
