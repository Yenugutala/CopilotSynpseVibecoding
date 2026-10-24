-- Reference pattern: sql/silver/NN_<table>.sql
-- Worked example for a hypothetical spec specs/sources/products.yaml (NOT a real spec in this repo):
--   business_key: [product_id]
--   dq_rules:
--     product_id_not_null   not_null        product_id                  reject
--     product_code_format   regex           product_code 'PRD-[0-9][0-9][0-9][0-9]'  reject
--     unit_price_valid      valid_type      unit_price                  reject
--     unit_price_min        min_value 0     unit_price                  reject
--     stock_qty_min         min_value 0     stock_qty                   reject
--     status_allowed        allowed_values  status [ACTIVE, DISCONTINUED]  reject
--     launch_date_valid     valid_type      launch_date                 reject
--     supplier_exists       references      supplier_id -> suppliers.supplier_id  warn
-- It is file 02 because the warn rule reads silver.suppliers, which is built by file 01.
-- Silver = typed, trimmed, DQ-checked, de-duplicated Parquet in curated/silver/<table>/run_id=<id>/.
-- Each pipeline run writes a NEW run_id folder, so CETAS never hits "folder not empty".
-- Only use placeholders inside SQL, never in comments.

-- Block 1: typed values + DQ flags (one helper view reused by the clean and rejects tables)
CREATE OR ALTER VIEW silver.products_checked AS
WITH typed AS (
    SELECT
        TRY_CAST(NULLIF(LTRIM(RTRIM(product_id)), '') AS INT)            AS product_id,
        UPPER(NULLIF(LTRIM(RTRIM(product_code)), ''))                    AS product_code,
        NULLIF(LTRIM(RTRIM(product_name)), '')                           AS product_name,
        NULLIF(LTRIM(RTRIM(category)), '')                               AS category,
        TRY_CAST(NULLIF(LTRIM(RTRIM(unit_price)), '') AS DECIMAL(10,2))  AS unit_price,
        NULLIF(LTRIM(RTRIM(unit_price)), '')                             AS unit_price_raw,
        TRY_CAST(NULLIF(LTRIM(RTRIM(stock_qty)), '') AS INT)             AS stock_qty,
        UPPER(NULLIF(LTRIM(RTRIM(status)), ''))                          AS status,
        TRY_CAST(NULLIF(LTRIM(RTRIM(supplier_id)), '') AS INT)           AS supplier_id,
        TRY_CAST(NULLIF(LTRIM(RTRIM(launch_date)), '') AS DATE)          AS launch_date,
        NULLIF(LTRIM(RTRIM(launch_date)), '')                            AS launch_date_raw,
        _source_file,
        _ingest_date
    FROM bronze.products
)
SELECT
    t.*,
    -- reject rules: one CASE each, producing '<rule_name>;' when the row fails
      CASE WHEN t.product_id IS NULL                                       THEN 'product_id_not_null;' ELSE '' END
    + CASE WHEN t.product_code IS NULL
             OR t.product_code NOT LIKE 'PRD-[0-9][0-9][0-9][0-9]'         THEN 'product_code_format;' ELSE '' END
    + CASE WHEN t.unit_price IS NULL AND t.unit_price_raw IS NOT NULL      THEN 'unit_price_valid;'    ELSE '' END
    + CASE WHEN t.unit_price < 0                                           THEN 'unit_price_min;'      ELSE '' END
    + CASE WHEN t.stock_qty < 0                                            THEN 'stock_qty_min;'       ELSE '' END
    + CASE WHEN t.status IS NULL OR t.status NOT IN ('ACTIVE', 'DISCONTINUED') THEN 'status_allowed;'  ELSE '' END
    + CASE WHEN t.launch_date IS NULL AND t.launch_date_raw IS NOT NULL    THEN 'launch_date_valid;'   ELSE '' END
      AS _dq_failures,
    -- warn rules: same shape, but the row stays in silver
      CASE WHEN NOT EXISTS (SELECT 1 FROM silver.suppliers AS s WHERE s.supplier_id = t.supplier_id)
                                                                           THEN 'supplier_exists;'     ELSE '' END
      AS _dq_warnings
FROM typed AS t;
GO

-- Block 2: drop the previous external table (metadata only; old Parquet files stay as history)
IF EXISTS (SELECT 1 FROM sys.external_tables WHERE name = 'products' AND schema_id = SCHEMA_ID('silver'))
    DROP EXTERNAL TABLE silver.products;
GO

-- Block 3: clean rows, one per business key (latest ingest wins; ties broken by row hash)
CREATE EXTERNAL TABLE silver.products
WITH (
    LOCATION    = 'silver/products/run_id={{run_id}}/',
    DATA_SOURCE = ds_curated,
    FILE_FORMAT = ff_parquet
)
AS
WITH hashed AS (
    SELECT
        p.*,
        CONVERT(VARCHAR(64), HASHBYTES('SHA2_256',
            CONCAT_WS('|', p.product_id, p.product_code, p.product_name, p.category, p.unit_price,
                           p.stock_qty, p.status, p.supplier_id, p.launch_date)), 2) AS _row_hash
    FROM silver.products_checked AS p
    WHERE p._dq_failures = ''
),
ranked AS (
    SELECT h.*, ROW_NUMBER() OVER (PARTITION BY h.product_id ORDER BY h._ingest_date DESC, h._row_hash DESC) AS _rn
    FROM hashed AS h
)
SELECT
    product_id,
    product_code,
    product_name,
    category,
    unit_price,
    stock_qty,
    status,
    supplier_id,
    launch_date,
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
IF EXISTS (SELECT 1 FROM sys.external_tables WHERE name = 'products_rejects' AND schema_id = SCHEMA_ID('silver'))
    DROP EXTERNAL TABLE silver.products_rejects;
GO

-- Block 5: rejects = rows that failed at least one reject rule (all columns kept for investigation)
CREATE EXTERNAL TABLE silver.products_rejects
WITH (
    LOCATION    = 'silver/products_rejects/run_id={{run_id}}/',
    DATA_SOURCE = ds_curated,
    FILE_FORMAT = ff_parquet
)
AS
SELECT
    p.*,
    CAST('{{run_id}}' AS VARCHAR(64)) AS _batch_id,
    SYSUTCDATETIME()                  AS _processed_ts
FROM silver.products_checked AS p
WHERE p._dq_failures <> '';
