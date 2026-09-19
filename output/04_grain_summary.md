# Grain & Table Summaries

## dbo.fact_sales
**Grain:** One row per sale transaction per customer, product, store and date

**Summary:** Central fact table capturing all sales transactions. Links customer, product, store and date dimensions. Key measures: amount, quantity, discount. Primary source for revenue and sales performance reporting.

---

## dbo.dim_customer
**Grain:** One row per unique customer

**Summary:** Customer master with demographic, segmentation and active-status attributes. SCD Type 1 — always reflects the latest record.

---

## dbo.dim_product
**Grain:** One row per unique product SKU

**Summary:** Product master including category hierarchy and list price. Referenced by sales and inventory fact tables.

---

## dbo.dim_date
**Grain:** One row per calendar date

**Summary:** Standard date dimension covering calendar attributes, fiscal periods and quarters. Joins to all time-variant fact tables.

---

## dbo.dim_store
**Grain:** One row per physical store location

**Summary:** Store master with city and country attributes, used to slice sales performance by geography.

---
