# Task 4 — Critical Thinking & Data Engineering Challenges

## 4.1 Data Ingestion & Integration Challenges

Chinook and Northwind both record sales, but their schemas were designed independently and describe different businesses. Integrating them at the accepted `FactSales` grain—one source transaction line—therefore requires controlled datatype conversion, explicit semantic mappings, source-aware identifiers, and validation. The inspected SQLite schemas remain the source of truth; the issues below distinguish confirmed structural differences from data-quality risks that ingestion must test.

| Challenge | Concrete Example | Engineering Risk | Handling in This Design |
| --- | --- | --- | --- |
| Heterogeneous key types | `Customer.CustomerId` is `INTEGER`; `Customers.CustomerID` is `TEXT`. | Directly loading both values into one key domain can cause conversion failures, ambiguous comparisons, or lost formatting. | Convert to target `TEXT` and build `CHINOOK:<id>` or `NORTHWIND:<id>` consistently in dimensions and fact foreign keys. |
| Cross-source key collisions | Chinook `Employee.EmployeeId` and Northwind `Employees.EmployeeID` are independent integer domains; the same risk applies to `Track.TrackId` and `Products.ProductID`. | Equal source values can incorrectly join records belonging to different people or products. | Use source-prefixed canonical customer, employee, product, and manager identifiers. Retain `DimSourceSystem` for provenance. |
| Naming and structural differences | `Customer`, `Employee`, `Track`, `Invoice`, and `InvoiceLine` correspond to `Customers`, `Employees`, `Products`, `Orders`, and `Order Details` only at a business-concept level. | Table renaming alone would miss different joins, grains, and attribute meanings. | Apply the accepted semantic mappings, including `Track`/`Products` → `DimProduct` and `InvoiceLine`/`Order Details` → `FactSales`. |
| Asymmetric attributes | Northwind `Customers` has no email column; Chinook has genre and composer data but no product category; Northwind has category data but no genre or composer. | Fabricated defaults could be mistaken for observed source values and distort reporting. | Store unavailable target attributes as `NULL` and preserve their source lineage. |
| Employee semantics | Northwind uses `Orders.EmployeeID` directly, while Chinook follows `Invoice` → `Customer` → `Customer.SupportRepId` → `Employee.EmployeeId`. | A technically valid join could support a misleading cross-business employee-performance comparison. | Keep `FactSales.EmployeeID` nullable and document that Chinook identifies the customer's assigned support representative, not a salesperson recorded on the invoice. |
| Measure rules | Both sources provide line `UnitPrice` and `Quantity`; Northwind `Order Details` also provides `Discount`. | Applying discount to only Northwind would give the unified `SalesAmount` two different meanings. | Calculate `SalesAmount = UnitPrice * Quantity` for both sources and exclude Northwind `Discount` under the accepted rule. |
| Date normalization | `Invoice.InvoiceDate` and `Orders.OrderDate` feed the shared `DimTime`; the target `DateKey` is `YYYYMMDD`. | Inconsistent parsing can create invalid keys, duplicate calendar members, or facts without a valid date. | Parse to a calendar date, derive `YYYYMMDD`, create one conformed row per date, and quarantine unparseable or missing required dates rather than inventing values. |
| Referential integrity and duplicates | Chinook identifies a line by `InvoiceLine.InvoiceLineId`; Northwind uses the composite `Order Details (OrderID, ProductID)` primary key. | Duplicate lines or unresolved customer, employee, product, order, or invoice references can inflate measures or break joins. | Validate source-line identity and every required lookup before loading; reject or quarantine invalid rows with a recorded reason. |
| Source provenance | `DimSourceSystem` defines `1 = Chinook` and `2 = Northwind`. | Without provenance, debugging and interpretation cannot reliably distinguish the two legacy meanings. | Populate `SourceSystemID` on every fact and use it with canonical-ID prefixes for traceability. |
| Uneven source volume | The EDA reports 2,240 Chinook `InvoiceLine` rows and 609,283 Northwind `Order Details` rows. | A single batch strategy may cause avoidable runtime, memory, and validation pressure on the larger source. | Size batches per source and design repeatable validation and incremental boundaries without changing the common fact grain. |

### Datatype and Identifier Standardization

The clearest datatype conflict is the customer business key. Chinook declares `Customer.CustomerId` as `INTEGER`, whereas Northwind declares `Customers.CustomerID` as `TEXT`. Loading both unchanged into one target column is unsafe: coercing Northwind identifiers such as `ALFKI` to integers would fail, while storing unqualified values as text would still not establish global uniqueness. The accepted target therefore uses `DimCustomer.CustomerID` as `TEXT`, with values such as `CHINOOK:59` and `NORTHWIND:ALFKI`.

The same normalization must be applied wherever the key appears. A dimension value of `CHINOOK:59` will not join to a fact value of `59`, so the transformation that builds `DimCustomer.CustomerID` must also build `FactSales.CustomerID` from the invoice or order header using the identical prefix, cast, and trimming rules. This consistency also applies to employee identifiers, product identifiers, and `DimEmployee.ReportsTo`.

Other confirmed source-type differences require explicit target conversions. Chinook commonly uses length-limited `NVARCHAR` columns while Northwind uses unconstrained SQLite `TEXT`; the conformed descriptive attributes use logical `TEXT`. Chinook prices are declared as `NUMERIC(10, 2)`, while Northwind uses `NUMERIC`; both must be converted through a decimal-compatible rule that preserves the intended precision. Chinook employee dates are declared `DATETIME` and Northwind employee dates as `DATE`, illustrating why parsing and target typing cannot rely only on a source type label. These are schema-level differences; the ingestion process must still profile actual values before assuming every value conforms to its declaration.

Primary keys also have only source-local meaning. An `EmployeeID` of `1` from Chinook and an `EmployeeID` of `1` from Northwind identify records in separate legacy namespaces, not necessarily the same person. Likewise, `TrackId` and `ProductID` values can overlap while representing unrelated products. This assignment resolves the problem with `CHINOOK:<id>` and `NORTHWIND:<id>` canonical values for customers, employees, and products. A production warehouse could instead introduce separate surrogate warehouse keys, but this project does not add them and retains its accepted source-prefixed IDs.

### Semantic and Structural Integration

The two sales paths are structurally different. Chinook uses `Customer` → `Invoice` → `InvoiceLine` → `Track`; Northwind uses `Customers` → `Orders` → `Order Details` → `Products`. The accepted mappings unify `Track` and `Products` in `DimProduct`, and map one `InvoiceLine` or one `Order Details` row to one `FactSales` row. Transaction dates also arrive through different headers: `Invoice.InvoiceDate` and `Orders.OrderDate` both feed `DimTime`. Similarly, `Customer.State` and `Customers.Region` feed the unified `DimCustomer.State` attribute. These transformations require semantic mapping and source-specific joins, not mechanical table or column renaming.

Employee integration needs an additional semantic warning. Northwind's `Orders.EmployeeID` directly identifies the employee associated with an order. A Chinook invoice has no employee column, so the project derives employee context through `Invoice` → `Customer` → `Customer.SupportRepId` → `Employee.EmployeeId`. The resulting values can join to one conformed `DimEmployee`, but they do not express the same event-level relationship: Chinook attributes the sale to the customer's assigned support representative. A report that labels both values simply as the salesperson who handled the transaction could therefore be misleading. The model preserves this limitation and keeps `FactSales.EmployeeID` nullable rather than inventing an employee.

### Missing Data and Data Quality

Some target NULLs are required by confirmed source asymmetry. Northwind `Customers` has no email column, so `DimCustomer.Email` is `NULL` for Northwind. Chinook tracks can supply `GenreName` through `Track.GenreId` → `Genre.Name` and can supply `Composer`, but have no accepted `CategoryName` source. Northwind products can supply `CategoryName` through `Products.CategoryID` → `Categories.CategoryName`, but do not supply `GenreName` or `Composer`. Those unavailable attributes remain `NULL`; values such as fake email addresses or invented categories and genres would destroy lineage.

Ingestion must also distinguish an unavailable concept from a present source field whose value is NULL. Both become a target NULL, but the lineage differs: “Northwind has no Email column” is a structural fact, while a NULL in a present optional field is a record-level observation. Transformation logs or metadata should preserve that distinction so later users do not interpret every NULL as the same quality problem.

No unverified defect should be treated as an observed fact. Instead, ingestion should test source primary-key uniqueness; non-null source line keys; duplicate `InvoiceLine.InvoiceLineId` values; duplicate Northwind `(OrderID, ProductID)` pairs; invoice/order header resolution; customer and employee lookup resolution where an identifier is present; required product resolution; parseable transaction dates; and non-null, convertible `Quantity` and `UnitPrice` values needed for measures. It should also check that canonical-ID construction does not create duplicates or malformed values.

When a check fails, the safe response is to reject or quarantine the affected row, log the validation rule and reason, and preserve the raw source record for investigation. The process should not silently fabricate a dimension member or substitute a plausible date, price, quantity, email, category, genre, or employee. These are required controls; this discussion does not claim that the inspected sources currently contain orphan keys, duplicates, or malformed values unless a project artifact explicitly demonstrates them.

### Measure and Date Consistency

At the shared line grain, Chinook supplies `InvoiceLine.UnitPrice` and `InvoiceLine.Quantity`; Northwind supplies `Order Details.UnitPrice`, `Order Details.Quantity`, and `Order Details.Discount`. The assignment-defined measure is `SalesAmount = UnitPrice * Quantity` for both sources. The ingestion layer must implement that formula consistently and use the transaction-line price, not the descriptive current price in `DimProduct`. Applying Northwind's discount while leaving Chinook undiscounted would change the meaning of the Northwind facts and invalidate direct aggregation across the two systems. A separate net or discount-adjusted measure could be defined under a future business rule, but it is not part of the current model.

For time integration, the process must parse `Invoice.InvoiceDate` and `Orders.OrderDate`, derive the calendar date, and generate an integer `DateKey` in `YYYYMMDD` form. One `DimTime` row should represent each distinct calendar date used by accepted facts. Missing or unparseable transaction dates need explicit rejection or quarantine because `FactSales.DateKey` is required; inventing a date would move sales into the wrong period. The source schemas do not provide documented timezone information, so this design does not assert or invent a timezone-conversion issue.

### Referential Integrity and Lineage

Dimensions and facts must be loaded with the same source-aware transformation rules. Before accepting a fact, ingestion should confirm that its `ProductID` resolves to `DimProduct`, its header resolves to `Invoice` or `Orders`, and each non-null customer or employee identifier resolves in the corresponding dimension. Nullable relationships must follow the contract: Northwind `Orders.CustomerID` and `Orders.EmployeeID` may be absent, and Chinook `Customer.SupportRepId` may be absent, so the related fact keys may remain `NULL`. A missing required product or usable transaction date is different and should not be silently accepted.

Every fact also receives `SourceSystemID`: `1` for Chinook and `2` for Northwind. This value supports cross-business reporting while retaining enough provenance to debug transformations and trace a warehouse row to the correct legacy system. Together, `DimSourceSystem` and the `CHINOOK:`/`NORTHWIND:` key prefixes prevent accidental cross-source joins and make semantic differences—especially employee attribution and product classification—visible during analysis.

### Operational Ingestion Considerations

The notebook's EDA output shows a substantial fact-source volume imbalance: 2,240 `InvoiceLine` rows compared with 609,283 `Order Details` rows. This does not by itself indicate that Northwind performs better; Task 3 also notes different transaction volumes and date coverage. Operationally, however, the skew affects extraction batch size, runtime, memory use, lookup-validation cost, retry scope, and reconciliation time. The larger source may require smaller bounded batches and source-specific incremental checkpoints, while both paths must still produce the same fact grain and pass the same business-rule validations.

Incremental processing would also need a stable source-specific boundary and duplicate protection so reruns do not add the same transaction line twice. The current assignment does not implement that pipeline. The important design principle is that operational tuning may differ by source, while canonical identifiers, measure definitions, conformed dates, lineage, and validation outcomes remain consistent.

## 4.2 Schema Evolution for a Third Acquisition

The first modeling question for a third acquisition is: **Does the third company's sales process have the same fundamental grain as `FactSales`: one sales transaction line item?** If yes, the preferred approach is to reuse `FactSales` and the existing conformed dimensions, extending the source mappings rather than redesigning the warehouse. If no, a fundamentally different business process should not be forced into `FactSales` merely to reuse the table.

| Change from Third Acquisition | Recommended Evolution | Why |
| --- | --- | --- |
| New source system | Add the conceptual member `3 = ThirdCompany` to `DimSourceSystem`; continue using `FactSales.SourceSystemID`. | Preserves provenance and enables source filtering and cross-business analysis without changing the fact structure. |
| New source IDs | Extend the namespace convention with values such as `THIRDCOMPANY:12345`. | Prevents cross-source primary-key collisions, accommodates different native ID types, and retains traceability. |
| Different source field names or joins | Create a source-to-target mapping from the new schema to the current conformed targets. | Source-specific naming and structure should be absorbed by semantic mapping when the business concepts remain equivalent. |
| Missing target attribute | Store `NULL`, such as when the new source has no email concept. | Avoids fabricating data and distinguishes unavailable information from observed values. |
| New descriptive attribute | Add a nullable attribute to an existing dimension only after establishing cross-business analytical value and a clear semantic home. | Prevents the model from accumulating unused, source-specific sparse columns. |
| New product classification | Map to `GenreName` or `CategoryName` only when the meaning is genuinely equivalent; otherwise retain `NULL` or evaluate a new nullable attribute. | Prevents unrelated classification systems from being mislabeled while preserving the simple star design. |
| Different employee role | Establish whether the source means salesperson, account manager, support representative, or another role before mapping it to `DimEmployee`. | An employee identifier alone does not prove semantic compatibility for BI comparisons. |
| Different pricing rules or dates | Admit the source to the shared measures and `DimTime` only through the existing semantic contracts. | Keeps revenue and time comparisons consistent across all businesses. |
| Different business-process grain | Consider a separate fact table that can share conformed dimensions. | Inventory snapshots, subscriptions, returns, service tickets, or shipments are not automatically sales transaction lines. |

### Extend the Existing Conformed Model

When the third company's process can produce one row per sales transaction line, the existing model already provides the integration framework. The new onboarding work is a mapping layer from the third source's business entities into the accepted targets:

- Third-source customer entity → `DimCustomer`
- Third-source employee or salesperson entity → `DimEmployee`
- Third-source product or item entity → `DimProduct`
- Third-source transaction date → `DimTime`
- Third-source sales line → `FactSales`
- Third-source identity → `DimSourceSystem`

These are conceptual roles, not claims about the third source's table or column names. Different names, joins, or storage types do not by themselves justify a target-schema change. If the business meaning and fact grain match, the source mapping should perform the required renaming, joining, type conversion, and normalization.

The smallest model extension is a new `DimSourceSystem` member: `3 = ThirdCompany`. Each accepted third-source fact would reference this member through the existing `FactSales.SourceSystemID`. Provenance would therefore remain available for debugging, source-specific filtering, cross-business reporting, and tracing a fact back to its legacy system, without adding a new fact column.

Canonical identifiers should extend in the same way. A conceptual source identifier `12345` becomes `THIRDCOMPANY:12345`, with the same transformation applied to the dimension primary key and every related `FactSales` foreign key. This preserves uniqueness and traceability even if the native ID is numeric, text, or overlaps an existing Chinook or Northwind value. The current assignment continues using prefixed canonical IDs; it does not introduce surrogate warehouse keys. Surrogate keys could be evaluated in a larger production implementation, but they are not required to onboard the hypothetical source under this design.

This approach also avoids source-specific schema expansion. Creating `DimChinookCustomer`, `DimNorthwindCustomer`, and `DimThirdCompanyCustomer`, or separate sales facts for each compatible source, would fragment equivalent concepts and undermine unified analysis. Conformed dimensions, `DimSourceSystem`, canonical IDs, and source-specific mappings provide the intended separation without duplicating the analytical schema.

### Preserve Semantic Consistency

Compatibility must be established by meaning, not by similar field names. The current model already demonstrates this with employees: Northwind records direct order attribution through `Orders.EmployeeID`, while Chinook derives the customer's assigned support representative through `Customer.SupportRepId`. A third source might describe an account manager, salesperson, or another employee relationship. Those are validation possibilities, not claims about an actual source. The team must determine the role represented before mapping it into `DimEmployee` and document how reports may compare it. If the role is not sufficiently compatible, the BI interpretation or a future model extension should change rather than silently relabeling the value.

The same principle applies to `FactSales.SalesAmount`. A third source should join the shared fact only if it can support the agreed line definition `UnitPrice * Quantity`. Onboarding must determine whether its line price is gross or net, whether tax is included, whether discounts are represented, and whether returns appear as negative sales. These are contract questions. The transformation must not automatically apply a source-specific tax or discount or reinterpret negative values, because doing so would give one column different meanings across sources. If a materially different measure is analytically necessary, it should be defined separately under an explicit future rule instead of changing the current `SalesAmount` or its Northwind discount exclusion.

The third source's transaction date should map to the same `DimTime` when it represents the same sales event. Ingestion should normalize it to `FullDate` and derive `DateKey = YYYYMMDD`; a separate company-specific date dimension is unnecessary. If a future process exposes several analytically important dates, such as order, ship, and return dates, role-playing relationships to the conformed date dimension or a different fact design could be evaluated. This is a future modeling option, not a change to the current assignment schema.

Onboarding should therefore be treated as data-contract testing. Before release, the team should validate source primary-key uniqueness, canonical-ID collision prevention, datatype conversions, required-field presence, foreign-key and dimension lookup resolution, valid dates, usable quantity and price fields, duplicate transaction-line detection, NULL handling, correct source-system attribution, measure reconciliation, and mapping completeness. A new source must not silently weaken existing BI definitions merely because its records can be loaded technically.

### Evolve Dimensions Carefully

Attribute onboarding falls into three cases. First, when an equivalent source attribute already exists in the target—such as a customer-city concept mapping to `DimCustomer.City`—it can be mapped directly or normalized to the accepted representation. Second, when the source lacks an existing attribute—such as a hypothetical absence of email—its `DimCustomer.Email` remains `NULL`; no value should be fabricated.

Third, a new source may introduce a useful descriptive attribute that the model does not currently contain. Before extending a dimension, the team should ask whether the attribute supports an actual BI requirement, has a stable meaning, belongs naturally in that dimension, and can be useful across more than one business. It should also assess whether the change would create many source-specific sparse columns. A genuinely useful attribute may be added as nullable in a future model revision, but the warehouse should not copy every available source field automatically.

Product classification illustrates the risk. Chinook contributes `GenreName`, while Northwind contributes `CategoryName`; both remain nullable attributes of `DimProduct`, not separate dimensions. If the third company uses another classification scheme, it should map to either existing attribute only when its business meaning is truly equivalent. Otherwise those attributes stay `NULL`, and a new nullable descriptive field should be considered only when analysis requires it. A separate classification dimension is justified only if the concept becomes important or complex enough to warrant one; the default remains the current simple star rather than immediate snowflaking.

### Introduce New Facts Only for New Grains

A new source with the same line-sale grain should extend mappings and conformed dimensions. A new business process or a different grain may instead require another fact table. Inventory snapshots, subscriptions, returns, service tickets, and shipments are illustrative examples of processes whose events, timing, and measures may not mean “one sales transaction line item.” The acquisition is hypothetical, so this document does not assert that ThirdCompany contains any of them.

Kimball-style dimensional modeling allows separate fact tables to share conformed dimensions. Conceptually, a future `FactInventory` or `FactReturns` could share `DimProduct`, `DimTime`, and `DimSourceSystem` with `FactSales` while preserving its own declared grain and measures. These names illustrate the decision rule only; no table is added to the accepted model. The principle is to reuse dimensions where meanings conform, but never mix incompatible events in `FactSales` merely to avoid creating an appropriate future fact.

### Preserve Backward Compatibility

Adding a compatible third source should be additive. Existing Chinook and Northwind dimension keys remain stable, existing `FactSales` rows do not need rewriting, source names remain unchanged, and the meanings of `SalesQuantity` and `SalesAmount` remain fixed. Existing BI queries and joins should continue to return the same two-source results until third-source facts are loaded.

Once `SourceSystemID = 3` and compatible facts are onboarded, an existing query pattern should naturally return another business without structural changes:

```sql
SELECT DimSourceSystem.SourceSystemName,
       SUM(FactSales.SalesAmount)
FROM FactSales
JOIN DimSourceSystem
  ON FactSales.SourceSystemID = DimSourceSystem.SourceSystemID
GROUP BY DimSourceSystem.SourceSystemName;
```

This backward compatibility is the main benefit of the current conformed design. The schema evolves through a new source member, canonical namespace, validated mappings, and carefully justified nullable attributes when needed. Only a genuinely different process or grain should trigger consideration of an additional fact, and even then the existing conformed dimensions can remain shared.

## 4.3 Data Lake vs Data Warehouse

A Data Lake and a Data Warehouse solve different but complementary problems for OmniCorp. A Data Lake is primarily a flexible store for large volumes of relatively raw or lightly processed data. It can retain structured, semi-structured, and unstructured data in source-aligned forms so that structure and interpretation can be applied when data is consumed or transformed—often described as schema-on-read. This flexibility does not remove the need for schemas, metadata, security, or governance.

A Data Warehouse is a curated, integrated, structured analytical store. Data is validated and transformed into predefined business structures before BI consumption—often described as schema-on-write. In this project, that analytical structure is the star schema formed by `FactSales`, `DimCustomer`, `DimEmployee`, `DimProduct`, `DimTime`, and `DimSourceSystem`. Schema-on-read and schema-on-write are useful general distinctions rather than absolute rules: a lake can contain well-structured datasets, and a warehouse environment may retain supporting data outside its primary curated layer.

| Aspect | Data Lake | Data Warehouse |
| --- | --- | --- |
| Primary purpose | Preserve flexible, source-aligned data for exploration, reprocessing, and future uses. | Deliver consistent business data for analytical queries and reporting. |
| Data form | Can contain structured, semi-structured, and unstructured data. | Primarily curated and structured around defined analytical concepts. |
| Schema approach | Structure may be retained from the source or applied when data is read and transformed. | Target structures and business rules are defined before data is published for use. |
| Transformation level | Raw or lightly processed data may coexist with validated source-aligned datasets. | Data is standardized, integrated, and mapped into conformed facts and dimensions. |
| Quality and governance | Requires metadata, lineage, access control, retention rules, profiling, and discoverability despite its flexibility. | Enforces stronger analytical contracts for datatypes, keys, grain, measures, and relationships. |
| Query experience | Users may need source knowledge and additional preparation before analysis. | Predictable structures support simpler, repeatable analytical SQL. |
| Typical users and workloads | Often supports data engineers, data scientists, exploration, source investigation, and reprocessing. | Often supports BI analysts, dashboards, management reporting, and governed metrics. These roles are not exclusive. |
| BI suitability | Useful as an input to BI preparation, but raw datasets may expose conflicting semantics. | Preferred consumption layer for stable cross-business KPIs and reporting. |
| Acquisition flexibility | Can land a new source before every attribute has a conformed warehouse mapping. | Publishes only the acquired data that satisfies established analytical definitions. |
| Historical preservation | Retains source representations and source-specific fields for audit or later transformation. | Retains integrated analytical history according to the warehouse model and loading rules. |

### Role of a Data Lake at OmniCorp

Conceptually, a Data Lake could preserve source-aligned extracts from Chinook and Northwind before unified transformation. Relevant Chinook examples include `Customer`, `Invoice`, `InvoiceLine`, `Track`, and `Employee`; Northwind examples include `Customers`, `Orders`, `Order Details`, `Products`, and `Employees`. These names illustrate current source structures, not a requirement that every source table must be copied unchanged into a lake.

Preserving source-aligned data provides several benefits. Engineers can trace a warehouse value back to its original representation, repeat a transformation after mapping rules change, and retain attributes that current BI requirements do not need. For example, `DimProduct` contains the conformed `CategoryName` and `GenreName` attributes, while the sources contain additional fields such as Chinook `Track.Milliseconds` and `Track.Bytes`, and Northwind `Products.QuantityPerUnit`, `Products.UnitsInStock`, and `Products.SupplierID`. A lake can retain those source-specific fields without turning every one into a sparse warehouse column.

The lake also preserves distinctions identified in Section 4.1. Chinook's integer `Customer.CustomerId` and Northwind's text `Customers.CustomerID` can remain in their original source types before the warehouse creates canonical `TEXT` values such as `CHINOOK:<id>` and `NORTHWIND:<id>`. Northwind `Order Details.Discount` should remain available in source-aligned data even though the current warehouse deliberately excludes it from `SalesAmount`. If OmniCorp later approves a separate discount-adjusted measure, the original discount values remain available for controlled reprocessing rather than being reconstructed.

Asymmetric attributes have the same separation of responsibility. Northwind has no customer email source column; Chinook provides genre information; Northwind provides category information. The lake can preserve what each source actually supplies, while the warehouse publishes `NULL` where a conformed target attribute is unavailable. This keeps source detail without fabricating values or exposing every source-specific field to BI users.

A useful lake cannot become an uncontrolled dumping ground. Each landed dataset still needs source-system identification, metadata, lineage, access controls, retention rules, quality profiling, and discoverability. Those controls make raw data understandable and safe enough for investigation and reprocessing; flexibility is not a substitute for governance.

### Role of the Data Warehouse at OmniCorp

The Data Warehouse is the preferred consumption layer for OmniCorp's current BI questions. Its `FactSales` grain is one sales transaction line item, and its conformed dimensions provide stable analytical views of customers, employees, products, dates, and source systems. The warehouse contract standardizes identifiers, preserves documented NULLs, enforces the shared date model, and defines `SalesAmount` as line `UnitPrice * Quantity` with Northwind discount excluded.

This model supports revenue comparisons between Chinook and Northwind, top-customer analysis, top products or tracks, employee analysis with the documented Chinook support-representative caveat, time-series reporting, and source-system comparisons. Task 3.2 demonstrates the intended query pattern: `SUM(FactSales.SalesAmount)` grouped by `DimSourceSystem.SourceSystemName`. BI users can work with one measure and one source dimension rather than understanding `InvoiceLine` versus `Order Details`, `Customer` versus `Customers`, `Track` versus `Products`, or the original customer-key datatype conflict.

The warehouse therefore does more than place data in a SQL database. It publishes agreed business semantics. Canonical identifiers, conformed dimensions, referential-integrity expectations, the line-item fact grain, and the `SalesAmount` definition make repeated queries comparable. BI analysts and managers receive a smaller, governed interface, while engineers and data scientists can still use source-aligned data for investigations or new transformations. These user boundaries are practical tendencies, not absolute restrictions.

### How the Layers Work Together

The responsibilities can be expressed as a conceptual flow:

```text
Source systems
      ↓
Data Lake / raw or source-aligned storage
      ↓
Validation + standardization + semantic mapping
      ↓
Data Warehouse / conformed star schema
      ↓
BI / reporting
```

The lake preserves source fidelity; the transformation step resolves the integration challenges from Section 4.1; and the warehouse exposes only approved analytical meaning. This division lets OmniCorp keep Northwind `Discount`, original identifiers, and source-specific product attributes while continuing to publish the unchanged warehouse measure, canonical keys, and conformed product attributes. Raw preservation makes future rule changes possible, while curated contracts prevent those changes from silently altering existing reports.

The same pattern supports the third acquisition discussed in Section 4.2. The lake could first land and identify ThirdCompany's source data, retain its original structure, and support profiling and mapping development without immediately adding every source attribute to BI tables. The warehouse would accept only business concepts that conform to the existing dimensions and one-line-sale fact grain, using `SourceSystemID = 3` and the conceptual `THIRDCOMPANY:<source id>` namespace. A genuinely different process or grain would still require separate modeling rather than being forced into `FactSales`.

This separation also creates two levels of quality responsibility. Lake governance establishes what arrived, where it came from, who can use it, how long it is retained, and what profiling found. Warehouse governance establishes whether data satisfies accepted datatypes, canonical identifiers, conformed dimensions, required lookups, the one-transaction-line grain, and the `UnitPrice * Quantity` measure definition. Both layers require controls, but they protect different promises.

### Recommendation

OmniCorp should use the two layers complementarily: a Data Lake as the flexible source-aligned ingestion and historical-retention layer, and a Data Warehouse as the curated, conformed analytical layer for BI. The lake provides flexibility, source preservation, reprocessing capability, and a practical landing point for acquisitions. The warehouse provides consistent business definitions, simpler queries, governed metrics, and stable reporting across companies.

The current DSI310 project primarily represents the Data Warehouse analytical layer: it defines the unified star schema, source-to-target mappings, canonical identifiers, measure rules, and BI usage. It does not physically implement a production Data Lake or a complete production Data Warehouse platform. The complementary architecture described here is a reasoned future operating model, not infrastructure already delivered by this repository.
