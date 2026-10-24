-- Generated from specs/models/customer_order_summary.yaml
-- grain: one row per customer_id
-- Gold = plain views over silver external tables. Views are always current: no data is copied.
CREATE OR ALTER VIEW gold.customer_order_summary AS
SELECT
    c.customer_id,
    c.first_name + ' ' + c.last_name                                  AS full_name,
    c.email,
    c.country,
    c.signup_date,
    COUNT(o.order_id)                                                 AS total_orders,
    COALESCE(SUM(o.quantity), 0)                                      AS total_quantity,
    CAST(COALESCE(SUM(o.quantity * o.unit_price), 0) AS DECIMAL(18,2)) AS total_revenue,
    MIN(o.order_date)                                                 AS first_order_date,   -- NULL when no orders
    MAX(o.order_date)                                                 AS last_order_date     -- NULL when no orders
FROM silver.customers AS c
LEFT JOIN silver.orders AS o
       ON o.customer_id = c.customer_id
      AND o.status <> 'CANCELLED'           -- filter in the ON clause so customers without orders are kept
GROUP BY
    c.customer_id, c.first_name, c.last_name, c.email, c.country, c.signup_date;
