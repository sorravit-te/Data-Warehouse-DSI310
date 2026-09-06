# Task 3.1 — การอ่านความหมายของ 1 แถวใน Fact Table

## ธุรกรรมต้นทางที่เลือกมา

ธุรกรรมที่เลือกคือ 1 แถวของ `Order Details` จาก Northwind เท่านั้น ระบุด้วย composite key จากต้นทาง `(OrderID 10248, ProductID 11)` โดยดึงค่าออเดอร์ ลูกค้า พนักงาน สินค้า และหมวดหมู่ มาจากฐานข้อมูล Northwind SQLite ปัจจุบัน

| ฟิลด์ต้นทาง | ค่า |
| --- | --- |
| `Order Details.OrderID` | `10248` |
| `Order Details.ProductID` | `11` |
| `Orders.CustomerID` | `VINET` |
| `Orders.EmployeeID` | `5` |
| `Orders.OrderDate` | `2016-07-04` |
| `Order Details.UnitPrice` | `14.00` |
| `Order Details.Quantity` | `12` |
| `Order Details.Discount` | `0.0` — เป็นค่าจากต้นทางเท่านั้น ไม่ถูกนำไปคิดใน `SalesAmount` |

## แถวใน FactSales ที่ได้จากการแปลง

| คอลัมน์ใน FactSales | ค่า |
| --- | --- |
| `DateKey` | `20160704` |
| `CustomerID` | `NORTHWIND:VINET` |
| `EmployeeID` | `NORTHWIND:5` |
| `ProductID` | `NORTHWIND:11` |
| `SourceSystemID` | `2` |
| `SalesQuantity` | `12` |
| `SalesAmount` | `168.00` |

`SalesAmount = UnitPrice × Quantity = 14.00 × 12 = 168.00`

## ข้อมูลบริบทจาก Dimension

| Dimension | Key | ความหมายเชิงธุรกิจ |
| --- | --- | --- |
| `DimTime` | `20160704` | วันที่: 4 กรกฎาคม 2016 |
| `DimCustomer` | `NORTHWIND:VINET` | Paul Henriot |
| `DimEmployee` | `NORTHWIND:5` | Steven Buchanan — Sales Manager |
| `DimProduct` | `NORTHWIND:11` | Queso Cabrales — สินค้าหมวดผลิตภัณฑ์นม (Dairy Products) |
| `DimSourceSystem` | `2` | Northwind |

## การตีความเชิงธุรกิจ

เมื่อวันที่ 4 กรกฎาคม 2016 รายการขาย 1 บรรทัดของ Northwind บันทึกว่าลูกค้า Paul Henriot ซื้อสินค้า Queso Cabrales จำนวน 12 หน่วย คิดเป็นยอดขาย (SalesAmount) 168.00 โดยออเดอร์นี้ถูกระบุว่าดำเนินการโดย Sales Manager Steven Buchanan โดยตรง

## การอ้างอิงถึง Dimension ทั้งหมด

ประโยคด้านบนอ้างอิงถึง dimension ครบทั้ง 5 ตัว:

- `DimTime`: 4 กรกฎาคม 2016
- `DimCustomer`: Paul Henriot
- `DimEmployee`: Steven Buchanan, Sales Manager
- `DimProduct`: Queso Cabrales
- `DimSourceSystem`: Northwind

## หมายเหตุการตีความ

- Grain ของ `FactSales` คือ 1 แถวต่อ 1 รายการสินค้าในธุรกรรมการขาย
- การระบุพนักงานของ Northwind มาจาก `Orders.EmployeeID` โดยตรง
- `SalesAmount` คือ `UnitPrice × Quantity`
- ส่วนลด (`Discount`) ของ Northwind ถูกตัดออกโดยตั้งใจ ไม่นำมาคิดใน `SalesAmount` ตามที่โจทย์กำหนด
