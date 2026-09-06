# Task 3.2 — ตัวอย่างรายงาน (BI Dashboard Mock-up)

## คำถามทางธุรกิจ

รายได้รวมของธุรกิจเพลง Chinook เทียบกับธุรกิจอาหารและเครื่องดื่ม Northwind เป็นอย่างไร?

## โมเดลการวิเคราะห์

- Measure: `SUM(FactSales.SalesAmount)`
- Dimension: `DimSourceSystem.SourceSystemName`
- การจัดกลุ่ม: Chinook เทียบกับ Northwind

`FactSales` มี 1 แถวต่อ 1 รายการสินค้าในธุรกรรมการขาย โดย `SalesAmount` คำนวณจาก `UnitPrice × Quantity` ของแถวต้นทาง และ `DimSourceSystem` ใช้ระบุว่าแต่ละแถวมาจาก Chinook หรือ Northwind

## ข้อมูลต้นทาง

| ธุรกิจ | Source system | ตารางต้นทาง | วิธีคำนวณรายได้ |
|---|---|---|---|
| เพลง | Chinook | `Invoice`, `InvoiceLine` | `InvoiceLine.UnitPrice × InvoiceLine.Quantity` |
| อาหารและเครื่องดื่ม | Northwind | `Orders`, `Order Details` | `Order Details.UnitPrice × Order Details.Quantity` |

ผลลัพธ์คำนวณตรงจากฐานข้อมูลต้นทาง SQLite ในเครื่องจริง โดยตั้งใจ**ไม่นำ**ส่วนลด (`Discount`) ของ Northwind มาคิด ตามคำนิยาม `SalesAmount` ใน dimensional model และไม่ใช้ค่า Freight หรือยอดรวมหัวบิลเป็น measure รายได้ เพื่อตรวจสอบความถูกต้องของข้อมูลต้นทาง ยอดรวมจาก line ของ Chinook ตรงกับผลรวมของ `Invoice.Total` ที่ 2,328.60 พอดี

## ผลลัพธ์

| Source system | ธุรกิจ | ยอดขายรวม (SalesAmount) | สัดส่วนของยอดรวมทั้งหมด |
|---|---|---:|---:|
| Chinook | เพลง | 2,328.60 | 0.0005% |
| Northwind | อาหารและเครื่องดื่ม | 448,475,298.72 | 99.9995% |
| **รวม** | **ทั้งสองธุรกิจ** | **448,477,627.32** | **100.0000%** |

ไม่แสดงสัญลักษณ์สกุลเงิน เนื่องจากข้อมูลต้นทางและการออกแบบ warehouse ปัจจุบันยังไม่ได้กำหนดสกุลเงินสำหรับการรายงานแบบรวมศูนย์

## การตีความเชิงธุรกิจ

จากชุดข้อมูลต้นทางที่ได้รับมา Northwind มีสัดส่วนรายได้ 99.9995% ของยอดรวมทั้งหมด ในขณะที่ Chinook มีเพียง 0.0005% ยอดรวมของ Northwind สูงกว่ายอดรวมของ Chinook ประมาณ 192,594.39 เท่า อย่างไรก็ตาม ชุดข้อมูลทั้งสองมีปริมาณธุรกรรมและช่วงวันที่ครอบคลุมแตกต่างกันมาก การเปรียบเทียบนี้จึงสะท้อน**เฉพาะข้อมูลชุดที่ให้มา** ไม่ใช่ผลประกอบการจริงของบริษัทในภาพรวม

## ตัวอย่างรายงาน / Dashboard Mock-up

![ตัวอย่าง dashboard เปรียบเทียบรายได้](bi_revenue_comparison_mockup.png)

## เส้นทางการตรวจสอบย้อนกลับจากต้นทางถึง Warehouse

- Chinook: `Invoice` → `InvoiceLine` → คำนวณ `UnitPrice × Quantity` ต่อบรรทัด → `FactSales.SalesAmount`
- Northwind: `Orders` → `Order Details` → คำนวณ `UnitPrice × Quantity` ต่อบรรทัด → `FactSales.SalesAmount`
- เส้นทางการวิเคราะห์บน dashboard: `FactSales` → `DimSourceSystem` จัดกลุ่มตาม `DimSourceSystem.SourceSystemName`
- ส่วนลด (`Discount`) ของ Northwind ถูกตัดออกจาก `SalesAmount` โดยยังคงเก็บไว้เป็นข้อมูลอ้างอิงจากต้นทางเท่านั้น
