# Column Data Types

## dbo.fact_sales

| Column       | Data Type   | Nullable   | PK   |
|:-------------|:------------|:-----------|:-----|
| sale_id      | INTEGER     | YES        | ✅    |
| sale_date    | TEXT        | YES        |      |
| customer_id  | INTEGER     | YES        |      |
| product_id   | INTEGER     | YES        |      |
| date_key     | INTEGER     | YES        |      |
| store_id     | INTEGER     | YES        |      |
| amount       | REAL        | YES        |      |
| quantity     | INTEGER     | YES        |      |
| discount_pct | REAL        | YES        |      |
| is_deleted   | INTEGER     | YES        |      |

## dbo.dim_customer

| Column            | Data Type   | Nullable   | PK   |
|:------------------|:------------|:-----------|:-----|
| customer_id       | INTEGER     | YES        | ✅    |
| customer_name     | TEXT        | NO         |      |
| email             | TEXT        | NO         |      |
| phone             | TEXT        | YES        |      |
| date_of_birth     | TEXT        | YES        |      |
| registration_date | TEXT        | YES        |      |
| segment           | TEXT        | YES        |      |
| address_id        | INTEGER     | YES        |      |
| is_active         | INTEGER     | YES        |      |

## dbo.dim_product

| Column       | Data Type   | Nullable   | PK   |
|:-------------|:------------|:-----------|:-----|
| product_id   | INTEGER     | YES        | ✅    |
| product_name | TEXT        | NO         |      |
| category     | TEXT        | YES        |      |
| sub_category | TEXT        | YES        |      |
| unit_price   | REAL        | YES        |      |

## dbo.dim_date

| Column        | Data Type   | Nullable   | PK   |
|:--------------|:------------|:-----------|:-----|
| date_key      | INTEGER     | YES        | ✅    |
| calendar_date | TEXT        | YES        |      |
| month_name    | TEXT        | YES        |      |
| quarter       | INTEGER     | YES        |      |
| fiscal_year   | INTEGER     | YES        |      |

## dbo.dim_store

| Column     | Data Type   | Nullable   | PK   |
|:-----------|:------------|:-----------|:-----|
| store_id   | INTEGER     | YES        | ✅    |
| store_name | TEXT        | YES        |      |
| city       | TEXT        | YES        |      |
| country    | TEXT        | YES        |      |
