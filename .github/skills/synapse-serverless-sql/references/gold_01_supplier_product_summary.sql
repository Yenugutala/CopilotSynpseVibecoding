-- Reference pattern: sql/gold/NN_<model>.sql
-- Worked example for a hypothetical model spec specs/models/supplier_product_summary.yaml (NOT a real spec in this repo):
--   grain: one row per supplier_id
--   join: silver.suppliers LEFT JOIN silver.products ON supplier_id   (suppliers without products are kept)
--   filters: products.status <> 'DISCONTINUED'
-- Gold = plain views over silver external tables. Views are always current: no data is copied.
CREATE OR ALTER VIEW gold.supplier_product_summary AS
SELECT
    s.supplier_id,
    s.supplier_name,
    s.country,
    COUNT(DISTINCT p.product_id)                                        AS active_products,
    COALESCE(SUM(p.stock_qty), 0)                                       AS total_stock_qty,
    CAST(COALESCE(SUM(p.stock_qty * p.unit_price), 0) AS DECIMAL(18,2)) AS total_stock_value,
    CAST(AVG(p.unit_price) AS DECIMAL(10,2))                            AS avg_unit_price,      -- NULL when no products
    MAX(p.launch_date)                                                  AS latest_launch_date
FROM silver.suppliers AS s
LEFT JOIN silver.products AS p
       ON p.supplier_id = s.supplier_id
      AND p.status <> 'DISCONTINUED'        -- filter in the ON clause so suppliers without products are kept
GROUP BY
    s.supplier_id, s.supplier_name, s.country;
