# Grain & Table Summaries

## dbo.fact_sales
**Grain:** One row per sale transaction per customer per product per date

**Summary:** Central fact table capturing all sales transactions. Each record represents a single sale event linking customer, product, store, and date dimensions. Key measures include amount, quantity, and discount. Used for revenue and sales performance reporting.

---

## dbo.dim_customer
**Grain:** One row per unique customer

**Summary:** Master dimension for all customers. Contains demographic, segmentation, and status attributes. Slowly Changing Dimension Type 1 — latest record only.

---

## dbo.dim_product
**Grain:** One row per unique product SKU

**Summary:** Product master dimension including category hierarchy and list price. Used across sales and inventory fact tables.

---

## dbo.dim_date
**Grain:** One row per calendar date

**Summary:** Standard date dimension covering calendar attributes, fiscal periods, and quarters. Joins to all time-variant fact tables.

---

## dbo.dim_store
**Grain:** One row per physical store location

**Summary:** Store master dimension with city and country attributes. Used to analyse sales by geography.

---
