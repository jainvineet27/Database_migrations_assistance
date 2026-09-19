-- Data Product : Sales_Daily
-- Generated   : 2026-09-19 19:48:16

SELECT
    f.sale_id,
    f.sale_date,
    f.amount,
    f.quantity,
    f.discount_pct,
    c.customer_id,
    c.customer_name,
    c.email        AS customer_email,
    c.region,
    c.segment,
    p.product_id,
    p.product_name,
    p.category,
    p.sub_category,
    p.unit_price,
    d.date_key,
    d.calendar_date,
    d.month_name,
    d.quarter,
    d.fiscal_year,
    s.store_id,
    s.store_name,
    s.city,
    s.country
FROM dbo.fact_sales f
INNER JOIN dbo.dim_customer  c ON f.customer_id  = c.customer_id
INNER JOIN dbo.dim_product   p ON f.product_id   = p.product_id
INNER JOIN dbo.dim_date      d ON f.date_key      = d.date_key
INNER JOIN dbo.dim_store     s ON f.store_id      = s.store_id
WHERE
    f.sale_date >= DATEADD(DAY, -1, CAST(GETDATE() AS DATE))
    AND f.is_deleted = 0
    AND c.is_active  = 1