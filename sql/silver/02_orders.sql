-- Generated from specs/sources/orders.yaml
-- business_key: [order_id]. File 02 because the warn rule customer_exists reads silver.customers, built by file 01.
-- Silver = typed, trimmed, DQ-checked, de-duplicated Parquet in curated/silver/<table>/run_id=<id>/.
-- Each pipeline run writes a NEW run_id folder, so CETAS never hits "folder not empty".

-- Block 1: typed values + DQ flags (one helper view reused by the clean and rejects tables)
CREATE OR ALTER VIEW silver.orders_checked AS
WITH typed AS (
    SELECT
        TRY_CAST(NULLIF(LTRIM(RTRIM(order_id)), '') AS INT)             AS order_id,
        NULLIF(LTRIM(RTRIM(order_id)), '')                              AS order_id_raw,
        TRY_CAST(NULLIF(LTRIM(RTRIM(customer_id)), '') AS INT)          AS customer_id,
        TRY_CAST(NULLIF(LTRIM(RTRIM(order_date)), '') AS DATE)          AS order_date,
        NULLIF(LTRIM(RTRIM(order_date)), '')                            AS order_date_raw,
        NULLIF(LTRIM(RTRIM(product)), '')                               AS product,
        TRY_CAST(NULLIF(LTRIM(RTRIM(quantity)), '') AS INT)             AS quantity,
        TRY_CAST(NULLIF(LTRIM(RTRIM(unit_price)), '') AS DECIMAL(10,2)) AS unit_price,
        UPPER(NULLIF(LTRIM(RTRIM(status)), ''))                         AS status,
        _source_file,
        _ingest_date
    FROM bronze.orders
)
SELECT
    t.*,
    -- reject rules: one CASE each, producing '<rule_name>;' when the row fails
      CASE WHEN t.order_id IS NULL                                         THEN 'order_id_not_null;'     ELSE '' END
    + CASE WHEN t.order_id IS NULL AND t.order_id_raw IS NOT NULL          THEN 'order_id_valid;'        ELSE '' END
    + CASE WHEN t.customer_id IS NULL                                      THEN 'customer_id_not_null;'  ELSE '' END
    + CASE WHEN t.order_date IS NULL                                       THEN 'order_date_not_null;'   ELSE '' END
    + CASE WHEN t.order_date IS NULL AND t.order_date_raw IS NOT NULL      THEN 'order_date_valid;'      ELSE '' END
    + CASE WHEN t.product IS NULL                                          THEN 'product_not_null;'      ELSE '' END
    + CASE WHEN t.quantity IS NULL                                         THEN 'quantity_not_null;'     ELSE '' END
    + CASE WHEN t.quantity < 1                                             THEN 'quantity_min;'          ELSE '' END
    + CASE WHEN t.unit_price IS NULL                                       THEN 'unit_price_not_null;'   ELSE '' END
    + CASE WHEN t.unit_price < 0                                           THEN 'unit_price_min;'        ELSE '' END
    + CASE WHEN t.status IS NULL
             OR t.status NOT IN ('PLACED', 'SHIPPED', 'DELIVERED', 'CANCELLED', 'RETURNED')
                                                                           THEN 'status_allowed;'        ELSE '' END
      AS _dq_failures,
    -- warn rules: same shape, but the row stays in silver
      CASE WHEN NOT EXISTS (SELECT 1 FROM silver.customers AS r WHERE r.customer_id = t.customer_id)
                                                                           THEN 'customer_exists;'       ELSE '' END
      AS _dq_warnings
FROM typed AS t;
GO

-- Block 2: drop the previous external table (metadata only; old Parquet files stay as history)
IF EXISTS (SELECT 1 FROM sys.external_tables WHERE name = 'orders' AND schema_id = SCHEMA_ID('silver'))
    DROP EXTERNAL TABLE silver.orders;
GO

-- Block 3: clean rows, one per business key (latest ingest wins; ties broken by row hash)
CREATE EXTERNAL TABLE silver.orders
WITH (
    LOCATION    = 'silver/orders/run_id={{run_id}}/',
    DATA_SOURCE = ds_curated,
    FILE_FORMAT = ff_parquet
)
AS
WITH hashed AS (
    SELECT
        o.*,
        CONVERT(VARCHAR(64), HASHBYTES('SHA2_256',
            CONCAT_WS('|', o.order_id, o.customer_id, o.order_date, o.product, o.quantity, o.unit_price, o.status)), 2) AS _row_hash
    FROM silver.orders_checked AS o
    WHERE o._dq_failures = ''
),
ranked AS (
    SELECT h.*, ROW_NUMBER() OVER (PARTITION BY h.order_id ORDER BY h._ingest_date DESC, h._row_hash DESC) AS _rn
    FROM hashed AS h
)
SELECT
    order_id,
    customer_id,
    order_date,
    product,
    quantity,
    unit_price,
    status,
    _dq_warnings,
    _row_hash,
    _source_file,
    _ingest_date,
    CAST('{{run_id}}' AS VARCHAR(64)) AS _batch_id,
    SYSUTCDATETIME()                  AS _processed_ts
FROM ranked
WHERE _rn = 1;
GO

-- Block 4: drop the previous rejects table
IF EXISTS (SELECT 1 FROM sys.external_tables WHERE name = 'orders_rejects' AND schema_id = SCHEMA_ID('silver'))
    DROP EXTERNAL TABLE silver.orders_rejects;
GO

-- Block 5: rejects = rows that failed at least one reject rule (all columns kept for investigation)
CREATE EXTERNAL TABLE silver.orders_rejects
WITH (
    LOCATION    = 'silver/orders_rejects/run_id={{run_id}}/',
    DATA_SOURCE = ds_curated,
    FILE_FORMAT = ff_parquet
)
AS
SELECT
    o.*,
    CAST('{{run_id}}' AS VARCHAR(64)) AS _batch_id,
    SYSUTCDATETIME()                  AS _processed_ts
FROM silver.orders_checked AS o
WHERE o._dq_failures <> '';
