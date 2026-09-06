# Task 2 — การออกแบบ Dimensional Model และโครงสร้าง Schema

> ข้อกำหนด (contract) ของ Kimball dimensional model แบบรวมศูนย์ สำหรับคลังข้อมูล (data warehouse) ของ OmniCorp

## 1. วัตถุประสงค์และขอบเขต

เอกสารนี้กำหนด "สัญญา" (contract) ของ Kimball dimensional model ในเชิง logical สำหรับ data warehouse ที่รวมข้อมูลจาก Chinook และ Northwind เข้าด้วยกัน โดยเป็นส่วนของ Task 2.1 เท่านั้น คือการกำหนด grain ของ fact, ตารางปลายทาง, ชนิดข้อมูลเชิง logical, กลยุทธ์การทำ key, ความสัมพันธ์ระหว่างตาราง, measure ต่างๆ, การตีความจากต้นทาง และขอบเขตที่รองรับด้าน BI — ก่อนที่จะสร้างแผนภาพหรือ implement จริง

การ mapping จาก Task 1.2 (source-to-target mapping) ที่ผ่านการยอมรับแล้ว ถือเป็นความจริงหลัก (source of truth) สำหรับการตัดสินใจในเอกสารนี้ ส่วน schema ของ SQLite ต้นทางที่ตรวจสอบไว้ ยังคงเป็นความจริงหลักสำหรับตาราง คอลัมน์ ชนิดข้อมูล primary key และ foreign key ของฝั่งต้นทาง

งานนี้**ไม่รวม**การทำ ETL จริง, การสร้างฐานข้อมูล warehouse จริง, การแก้ไขฐานข้อมูลต้นทางทั้งสอง, หรือ deliverable ของ Task 3/Task 4 ชนิดข้อมูลปลายทางที่ระบุด้านล่างเป็นชนิดข้อมูลเชิง logical เท่านั้น ส่วน syntax เฉพาะของฐานข้อมูลจริง ความละเอียด (precision) และ constraint ต่างๆ จะสรุปในภายหลัง

## 2. โครงสร้าง Star Schema

`FactSales` คือ fact table หลักที่อยู่ตรงกลาง โดย dimension ทั้ง 5 ตัวเชื่อมเข้ากับ fact table นี้โดยตรง

| Dimension | Foreign key ใน FactSales | Primary key ของ Dimension | ความสัมพันธ์ (Cardinality) |
| ------------------- | --------------------- | ---------------------------------- | ----------------------------------- |
| `DimTime` | `DateKey` | `DimTime.DateKey` | 1 แถวใน dimension ต่อหลายแถวใน fact |
| `DimCustomer` | `CustomerID` | `DimCustomer.CustomerID` | 1 แถวใน dimension ต่อหลายแถวใน fact |
| `DimEmployee` | `EmployeeID` | `DimEmployee.EmployeeID` | 1 แถวใน dimension ต่อหลายแถวใน fact |
| `DimProduct` | `ProductID` | `DimProduct.ProductID` | 1 แถวใน dimension ต่อหลายแถวใน fact |
| `DimSourceSystem` | `SourceSystemID` | `DimSourceSystem.SourceSystemID` | 1 แถวใน dimension ต่อหลายแถวใน fact |

โมเดลนี้ยังคงเป็น star schema (ไม่ใช่ snowflake) โดย Category, Genre, Artist, Album, Supplier, Geography และ entity อื่นๆ จากต้นทาง จะไม่ถูกแยกเป็น dimension เพิ่มเติมสำหรับงานชิ้นนี้ ป้าย category/genre ที่เกี่ยวข้องจะถูก "ตี flat" รวมเข้าไปใน `DimProduct` ส่วน attribute ด้านภูมิศาสตร์ของลูกค้าและพนักงานยังคงอยู่ใน dimension ของตัวเอง

การเลือกใช้ star schema เหมาะสมกับการใช้งานด้าน BI/รายงานของโจทย์นี้ เพราะ `FactSales` เป็น fact table หลักที่แต่ละ dimension ทางธุรกิจเชื่อมเข้ามาโดยตรง ทำให้การ join ในการ query ง่ายขึ้น และการรวมยอด (aggregate) ทั่วไป เช่น รายได้ตามลูกค้า สินค้า พนักงาน วันที่ หรือ source system ทำได้ตรงไปตรงมา การใช้ conformed dimension ทำให้มองข้อมูลจาก Chinook และ Northwind ในมุมเดียวกันได้ ในขณะที่ยังคงรักษาระดับความละเอียด (grain) ระดับ line-item ของ `FactSales` ตามที่โจทย์ต้องการ

## 3. Grain ของ FactSales

Grain ที่กำหนดคือ:

> 1 แถว ต่อ 1 รายการสินค้าในธุรกรรมการขาย (1 line item)

การตีความจากต้นทางแต่ละฝั่ง:

- Chinook: 1 แถว ต่อ 1 แถวใน `InvoiceLine`
- Northwind: 1 แถว ต่อ 1 แถวใน `Order Details`

การกำหนด grain ระดับ line-item ทำให้เก็บรายละเอียดการขายที่ละเอียดที่สุดเท่าที่โจทย์ต้องการไว้ได้ครบ แต่ละแถวใน fact จะระบุสินค้าที่ขาย ลูกค้า พนักงานที่เกี่ยวข้อง (ตามการตีความของแต่ละต้นทาง) วันที่ทำธุรกรรม และ source system ต้นทาง ทำให้วิเคราะห์ได้ทั้งระดับสินค้า ลูกค้า พนักงาน วันที่ และ source system โดยไม่ต้องเฉลี่ยยอดรวมจากระดับหัวบิล (header) และไม่เสียรายละเอียดระดับสินค้าไป

ไม่มีการกำหนด surrogate key แยกต่างหากให้ `FactSales` เพราะโจทย์ไม่ได้บังคับ และ contract ของ fact table นี้มีเพียง 7 attribute ตามที่ระบุด้านล่าง

## 4. FactSales

| คอลัมน์ | ชนิดข้อมูลเชิง Logical | หน้าที่และคำนิยาม |
| ------------------ | ------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DateKey` | `INTEGER` | Foreign key ไปยัง `DimTime.DateKey`; ได้มาจาก `Invoice.InvoiceDate` หรือ `Orders.OrderDate` แปลงเป็นรูปแบบ `YYYYMMDD` กรณีที่วันที่ต้นทางขาดหายไป ต้องตัดสินใจใน ETL ภายหลังอย่างชัดเจน ห้ามสร้างค่าขึ้นมาเอง |
| `CustomerID` | `TEXT` | Foreign key ไปยัง `DimCustomer.CustomerID`; ใช้รหัสลูกค้าที่ผ่านการ prefix ตามต้นทางแล้ว ออเดอร์ของ Northwind ที่ไม่มีลูกค้าจะปล่อยเป็น `NULL` |
| `EmployeeID` | `TEXT`, เป็น NULL ได้ | Foreign key ไปยัง `DimEmployee.EmployeeID`; ใช้รหัสพนักงานที่ผ่านการ prefix ตามต้นทางแล้ว เป็น NULL ได้เพราะบางความสัมพันธ์ต้นทางอาจไม่มี และ Chinook อ้างอิงความสัมพันธ์นี้แบบทางอ้อม |
| `ProductID` | `TEXT` | Foreign key ไปยัง `DimProduct.ProductID`; ใช้รหัสสินค้าที่ผ่านการ prefix ตามต้นทางแล้ว ทั้งสองต้นทางต้องมีการอ้างอิงสินค้าเสมอ |
| `SourceSystemID` | `INTEGER` | Foreign key ไปยัง `DimSourceSystem.SourceSystemID`; `1` คือ Chinook และ `2` คือ Northwind |
| `SalesQuantity` | `INTEGER` | Measure แบบบวกรวมได้ (additive) คัดลอกมาจาก `Quantity` ของแถวต้นทาง |
| `SalesAmount` | `NUMERIC` / เทียบเท่า `DECIMAL` | Measure แบบบวกรวมได้ คำนวณจาก `UnitPrice * Quantity` ของแถวต้นทาง |

### 4.1 การตีความจากต้นทาง

| Attribute ของ Fact | Chinook | Northwind |
| ------------------ | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `DateKey` | `InvoiceLine.InvoiceId -> Invoice.InvoiceId -> Invoice.InvoiceDate` | `Order Details.OrderID -> Orders.OrderID -> Orders.OrderDate` |
| `CustomerID` | `InvoiceLine.InvoiceId -> Invoice.CustomerId` แล้วเติม prefix ของ Chinook | `Order Details.OrderID -> Orders.CustomerID` แล้วเติม prefix ของ Northwind |
| `EmployeeID` | `InvoiceLine -> Invoice -> Customer -> Customer.SupportRepId -> Employee.EmployeeId` | `Order Details -> Orders.EmployeeID -> Employees.EmployeeID` |
| `ProductID` | `InvoiceLine.TrackId -> Track.TrackId` แล้วเติม prefix ของ Chinook | `Order Details.ProductID -> Products.ProductID` แล้วเติม prefix ของ Northwind |
| `SourceSystemID` | ค่าคงที่ `1` | ค่าคงที่ `2` |
| `SalesQuantity` | `InvoiceLine.Quantity` | `Order Details.Quantity` |
| `SalesAmount` | `InvoiceLine.UnitPrice * InvoiceLine.Quantity` | `Order Details.UnitPrice * Order Details.Quantity` |

### 4.2 Measure และการจัดการส่วนลด (Discount)

`SalesQuantity` มีค่าเท่ากับ `Quantity` ของแถวต้นทาง

`SalesAmount` มีค่าเท่ากับ `UnitPrice * Quantity` ของแถวต้นทาง

ส่วนลด `Order Details.Discount` ของ Northwind **ไม่ถูกนำมาคิด**ใน `SalesAmount` อาจพิจารณาสร้าง measure แยกที่หักส่วนลดในงาน modeling ครั้งถัดไป แต่ไม่ใช่ส่วนหนึ่งของ `SalesAmount` ตามที่โจทย์กำหนด และจะไม่ถูกเพิ่มเข้าไปใน contract นี้

### 4.3 ความหมายของ Employee

สำหรับ Chinook, `FactSales.EmployeeID` ได้มาแบบทางอ้อมผ่าน:

`Invoice -> Customer -> Customer.SupportRepId -> Employee.EmployeeId`

พนักงานคนนี้คือ support representative ที่ถูก assign ให้ลูกค้ารายนั้น **ไม่ใช่**พนักงานที่ถูกบันทึกไว้ตรงๆ บนใบแจ้งหนี้หรือรายการขายของ Chinook ดังนั้นการวิเคราะห์ผลงานพนักงานของ Chinook จึงต้องตีความว่าเป็นยอดขายที่ผูกกับ support representative ที่ดูแลลูกค้ารายนั้น ไม่ใช่การระบุคนขายโดยตรง

สำหรับ Northwind, `FactSales.EmployeeID` ได้มาโดยตรงจาก `Orders.EmployeeID` และเนื่องจากความสัมพันธ์นี้ในต้นทางฝั่งใดฝั่งหนึ่งอาจไม่มี คอลัมน์ `FactSales.EmployeeID` จึงเป็น NULL ได้

## 5. DimCustomer

| คอลัมน์ | ชนิดข้อมูลเชิง Logical | Contract |
| ---------------- | --------------------- | ----------------------------------------------------------------------------------------------------- |
| `CustomerID` | `TEXT`, primary key | รหัสลูกค้าที่ผ่านการ prefix ตามต้นทางแล้ว |
| `CustomerName` | `TEXT` | Chinook ใช้ `Customer.FirstName + Customer.LastName` (ตัดช่องว่างส่วนเกิน); Northwind ใช้ `Customers.ContactName` |
| `CompanyName` | `TEXT`, เป็น NULL ได้ | `Customer.Company` หรือ `Customers.CompanyName` |
| `City` | `TEXT`, เป็น NULL ได้ | `Customer.City` หรือ `Customers.City` |
| `State` | `TEXT`, เป็น NULL ได้ | `Customer.State` หรือ `Customers.Region` ที่ปรับให้เป็นมาตรฐานแล้ว |
| `Country` | `TEXT`, เป็น NULL ได้ | `Customer.Country` หรือ `Customers.Country` |
| `PostalCode` | `TEXT`, เป็น NULL ได้ | `Customer.PostalCode` หรือ `Customers.PostalCode` |
| `Phone` | `TEXT`, เป็น NULL ได้ | `Customer.Phone` หรือ `Customers.Phone` |
| `Email` | `TEXT`, เป็น NULL ได้ | `Customer.Email` สำหรับ Chinook; เป็น `NULL` สำหรับ Northwind เพราะตาราง `Customers` ไม่มีคอลัมน์อีเมล |

กลยุทธ์การทำ key คือ:

- Chinook: `CHINOOK:<Customer.CustomerId>`
- Northwind: `NORTHWIND:<Customers.CustomerID>`

การเติม prefix ตามต้นทางป้องกันไม่ให้รหัสจากสองต้นทางชนกัน และยังช่วยรวมความต่างของชนิดข้อมูล — `CustomerId` ของ Chinook เป็น `INTEGER` ส่วน `CustomerID` ของ Northwind เป็น `TEXT` — ให้กลายเป็น key ชนิด `TEXT` เดียวกันในฝั่ง warehouse

## 6. DimEmployee

| คอลัมน์ | ชนิดข้อมูลเชิง Logical | Contract |
| ---------------- | --------------------- | ----------------------------------------------------------------------------------- |
| `EmployeeID` | `TEXT`, primary key | รหัสพนักงานที่ผ่านการ prefix ตามต้นทางแล้ว |
| `EmployeeName` | `TEXT` | `FirstName + LastName` จากต้นทาง (ตัดช่องว่างส่วนเกิน) |
| `Title` | `TEXT`, เป็น NULL ได้ | `Employee.Title` หรือ `Employees.Title` |
| `City` | `TEXT`, เป็น NULL ได้ | `Employee.City` หรือ `Employees.City` |
| `Country` | `TEXT`, เป็น NULL ได้ | `Employee.Country` หรือ `Employees.Country` |
| `ReportsTo` | `TEXT`, เป็น NULL ได้ | รหัสหัวหน้างานจากต้นทาง แปลงให้อยู่ใน namespace ของพนักงานที่ prefix ตามต้นทางเดียวกัน |

กลยุทธ์การทำ key คือ:

- Chinook: `CHINOOK:<Employee.EmployeeId>`
- Northwind: `NORTHWIND:<Employees.EmployeeID>`

`ReportsTo` เก็บโครงสร้างสายบังคับบัญชาไว้ภายใน namespace ของต้นทางเดิม:

- Chinook: `CHINOOK:<Employee.ReportsTo>` ถ้ามีค่า
- Northwind: `NORTHWIND:<Employees.ReportsTo>` ถ้ามีค่า

สายบังคับบัญชานี้เป็นเพียงการอ้างอิงตัวเอง (self-reference) ในระดับ attribute ภายใน `DimEmployee` เท่านั้น ไม่ได้สร้าง dimension ใหม่ และไม่ทำให้โมเดลกลายเป็น snowflake

## 7. DimProduct

| คอลัมน์ | ชนิดข้อมูลเชิง Logical | Contract |
| ---------------- | --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ProductID` | `TEXT`, primary key | รหัสสินค้าที่ผ่านการ prefix ตามต้นทางแล้ว |
| `ProductName` | `TEXT` | `Track.Name` สำหรับ Chinook หรือ `Products.ProductName` สำหรับ Northwind |
| `CategoryName` | `TEXT`, เป็น NULL ได้ | เป็น `NULL` สำหรับ Chinook; `Categories.CategoryName` สำหรับ Northwind ผ่าน `Products.CategoryID` |
| `GenreName` | `TEXT`, เป็น NULL ได้ | `Genre.Name` สำหรับ Chinook ผ่าน `Track.GenreId`; เป็น `NULL` สำหรับ Northwind |
| `Composer` | `TEXT`, เป็น NULL ได้ | `Track.Composer` สำหรับ Chinook; เป็น `NULL` สำหรับ Northwind |
| `UnitPrice` | `NUMERIC`, เป็น NULL ได้ | `Track.UnitPrice` หรือ `Products.UnitPrice` ค่านี้เป็นแค่ attribute เชิงบรรยายของ dimension ไม่ได้แทนที่ราคาต่อบรรทัดที่ใช้คำนวณ `FactSales.SalesAmount` |

กลยุทธ์การทำ key คือ:

- Chinook: `CHINOOK:<Track.TrackId>`
- Northwind: `NORTHWIND:<Products.ProductID>`

สำหรับ Chinook สินค้าคือ `Track` หนึ่งเพลง โดย `GenreName` มาจาก `Genre`, `CategoryName` เป็น `NULL` และ `Composer` มาจาก `Track.Composer`

สำหรับ Northwind สินค้าคือ 1 แถวใน `Products` โดย `CategoryName` มาจาก `Categories.CategoryName` ส่วน `GenreName` และ `Composer` เป็น `NULL`

Album และ Artist จะไม่ถูกนับเป็น Category และ Supplier จะไม่ถูกนับเป็น Genre แนวคิดที่ไม่มีคู่เทียบข้ามต้นทางจะปล่อยเป็น `NULL` แทนที่จะยัดเข้าไปในความหมายที่ไม่เกี่ยวข้องกัน

## 8. DimTime

| คอลัมน์ | ชนิดข้อมูลเชิง Logical | Contract |
| -------------- | ------------------------ | --------------------------------------------------------------------------- |
| `DateKey` | `INTEGER`, primary key | Key ของวันที่ปฏิทิน รูปแบบ `YYYYMMDD` |
| `FullDate` | `DATE` | วันที่ปฏิทิน ได้จาก datetime ของธุรกรรมต้นทาง |
| `DayOfMonth` | `INTEGER` | วันที่ในเดือน ได้จาก `FullDate` |
| `DayOfWeek` | `TEXT` | ชื่อวันในสัปดาห์ ได้จาก `FullDate` |
| `Month` | `INTEGER` | เดือนตามปฏิทิน ได้จาก `FullDate` |
| `Quarter` | `INTEGER` | ไตรมาสตามปฏิทิน ค่า `1` ถึง `4` ได้จาก `FullDate` |
| `Year` | `INTEGER` | ปีตามปฏิทิน ได้จาก `FullDate` |

วันที่ต้นทางที่นำมาใช้คือ `Invoice.InvoiceDate` สำหรับ Chinook และ `Orders.OrderDate` สำหรับ Northwind

`DimTime` เป็น conformed calendar dimension เดียวที่ใช้ร่วมกันทั้งสองต้นทาง มี 1 แถวต่อ 1 วันที่ปฏิทินที่ไม่ซ้ำกัน ไม่ใช่ 1 แถวต่อ 1 ธุรกรรม โดย datetime ต้นทางจะถูกตัดเหลือแค่ส่วนวันที่ปฏิทิน ก่อนจะนำไปคำนวณ key และ attribute อื่นๆ

## 9. DimSourceSystem

| คอลัมน์ | ชนิดข้อมูลเชิง Logical | Contract |
| -------------------- | ------------------------ | ---------------------------------- |
| `SourceSystemID` | `INTEGER`, primary key | รหัส source system แบบคงที่ |
| `SourceSystemName` | `TEXT` | ชื่อ source system ที่อ่านเข้าใจง่าย |

สมาชิกที่กำหนดไว้แบบคงที่:

| SourceSystemID | SourceSystemName |
| -------------: | ---------------- |
| `1` | Chinook |
| `2` | Northwind |

Dimension นี้ระบุว่าแต่ละแถวใน fact มีที่มาจากธุรกิจไหน ทำให้ผู้ใช้งาน BI สามารถเปรียบเทียบผลงานระหว่างสองธุรกิจที่ถูกควบรวมเข้ามาได้

## 10. การรองรับความต้องการด้าน BI

| คำถามจากโจทย์ | Measure/การคำนวณใน FactSales | Dimension ที่ใช้ | ลักษณะการวิเคราะห์ |
| ------------------------------- | --------------------------------------------------------------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| รายได้: เพลง เทียบกับ อาหาร/เครื่องดื่ม | `SUM(FactSales.SalesAmount)` | `DimSourceSystem` | Group by `DimSourceSystem.SourceSystemName`; Chinook แทนธุรกิจเพลง ส่วน Northwind แทนธุรกิจอาหาร/เครื่องดื่มและสินค้าอื่นๆ |
| ลูกค้า Top 10 | `SUM(FactSales.SalesAmount)`; อาจใช้ `SUM(FactSales.SalesQuantity)` ร่วมด้วย | `DimCustomer`, อาจใช้ `DimSourceSystem` ร่วมด้วย | Group by รหัส/ชื่อลูกค้า เรียงรายได้จากมากไปน้อย แล้วเลือก 10 อันดับแรก dimension ของ source system ใช้แยกหรือเทียบระหว่างสองธุรกิจได้ |
| สินค้า/เพลง ที่ขายดีที่สุด | `SUM(FactSales.SalesAmount)` และ `SUM(FactSales.SalesQuantity)` | `DimProduct`, อาจใช้ `DimSourceSystem` ร่วมด้วย | Group by รหัส/ชื่อสินค้า; ใช้ genre สำหรับ Chinook หรือ category สำหรับ Northwind ถ้ามีข้อมูล |
| ผลงานพนักงาน | `SUM(FactSales.SalesAmount)` และอาจใช้ `SUM(FactSales.SalesQuantity)` ร่วมด้วย | `DimEmployee.EmployeeID`, `DimEmployee.EmployeeName`, `DimEmployee.Title`; อาจใช้ `DimSourceSystem.SourceSystemName` ร่วมด้วย | Group by รหัส/ชื่อพนักงาน วิเคราะห์แยกตามตำแหน่งได้ สำหรับ Chinook, `FactSales.EmployeeID` มาจาก `Customer.SupportRepId` ผลลัพธ์จึงแทนยอดขายที่ผูกกับ support representative ของลูกค้า ไม่ใช่พนักงานที่ถูกระบุเป็นผู้ขายบนใบแจ้งหนี้โดยตรง สำหรับ Northwind, `FactSales.EmployeeID` มาจาก `Orders.EmployeeID` โดยตรง และแทนพนักงานที่รับผิดชอบออเดอร์จริง `DimEmployee.Title` ใช้วิเคราะห์ตามตำแหน่งได้ รวมถึงตำแหน่ง support agent ของ Chinook ถ้าข้อมูลต้นทางมี |
| วิเคราะห์ตามวันที่ | `SUM(FactSales.SalesAmount)` และ `SUM(FactSales.SalesQuantity)` | `DimTime` | Group หรือ filter ตามวันที่ วัน เดือน ไตรมาส หรือปี |
| วิเคราะห์ตาม source system | `SUM(FactSales.SalesAmount)` และ `SUM(FactSales.SalesQuantity)` | `DimSourceSystem` | เปรียบเทียบรายได้และปริมาณระหว่าง Chinook และ Northwind |

## 11. การตัดสินใจในการออกแบบและข้อสมมติ

| การตัดสินใจ | Contract |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| รหัสอ้างอิงมาตรฐาน (Canonical identifiers) | รหัสลูกค้า พนักงาน สินค้า และรหัสหัวหน้างาน ใช้ prefix `CHINOOK:` หรือ `NORTHWIND:` เพื่อป้องกันการชนกันข้ามต้นทาง และทำให้ชนิดข้อมูล key ที่ต่างกันของแต่ละต้นทางเป็นมาตรฐานเดียวกัน |
| Attribute ที่ขาดหายไป | ใช้ `NULL` เมื่อ attribute หรือความสัมพันธ์ที่ไม่บังคับไม่มีข้อมูลต้นทาง ห้ามสร้างค่าขึ้นมาเอง |
| Grain ของ Fact | `FactSales` มี 1 แถวต่อ 1 รายการสินค้าในธุรกรรมการขาย: 1 แถวของ `InvoiceLine` หรือ 1 แถวของ `Order Details` |
| ยอดขาย (Sales amount) | `SalesAmount` คือ `UnitPrice * Quantity` ของแถวต้นทาง |
| ส่วนลดของ Northwind | `Order Details.Discount` ไม่ถูกนำมาคิดใน `SalesAmount` ตามที่โจทย์กำหนด อาจพิจารณาสร้าง measure ยอดขายสุทธิแยกในภายหลัง |
| ข้อจำกัดเรื่องพนักงานของ Chinook | Chinook ระบุ support representative ของลูกค้าผ่าน `Customer.SupportRepId` เท่านั้น ไม่มีการบันทึกพนักงานไว้ตรงๆ บนใบแจ้งหนี้หรือรายการขาย |
| ชนิดข้อมูลเชิง Logical | ชนิดข้อมูลที่ระบุไว้เป็นชนิดข้อมูลเชิง logical ที่เสนอไว้เท่านั้น ส่วน syntax ฐานข้อมูลจริง ความละเอียด และ constraint อยู่นอกขอบเขตของ Task 2.1 |
| รูปแบบ Schema | Dimension ทั้ง 5 ตัวเชื่อมเข้ากับ `FactSales` โดยตรง ไม่มีการสร้าง dimension แยกย่อยแบบ snowflake สำหรับ category, genre, artist, album, supplier, geography หรืออื่นๆ |
| ขอบเขตการ Implement | Task 2.1 กำหนดและบันทึก contract ของโมเดลเท่านั้น ไม่รวมการทำ ETL จริงหรือสร้างฐานข้อมูล warehouse จริง |
