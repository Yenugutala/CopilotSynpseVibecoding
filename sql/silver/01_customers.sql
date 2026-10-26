-- Generated from specs/sources/customers.yaml
-- Silver = typed, trimmed, DQ-checked, de-duplicated Parquet in curated/silver/<table>/run_id=<id>/.
-- Each pipeline run writes a NEW run_id folder, so CETAS never hits "folder not empty".

-- Block 1: typed values + DQ flags (one helper view reused by the clean and rejects tables)
CREATE OR ALTER VIEW silver.customers_checked AS
WITH typed AS (
    SELECT
        TRY_CAST(NULLIF(LTRIM(RTRIM(customer_id)), '') AS INT)   AS customer_id,
        NULLIF(LTRIM(RTRIM(first_name)), '')                     AS first_name,
        NULLIF(LTRIM(RTRIM(last_name)), '')                      AS last_name,
        LOWER(NULLIF(LTRIM(RTRIM(email)), ''))                   AS email,
        UPPER(NULLIF(LTRIM(RTRIM(country)), ''))                 AS country,
        TRY_CAST(NULLIF(LTRIM(RTRIM(signup_date)), '') AS DATE)  AS signup_date,
        NULLIF(LTRIM(RTRIM(signup_date)), '')                    AS signup_date_raw,
        _source_file,
        _ingest_date
    FROM bronze.customers
)
SELECT
    t.*,
    -- reject rules: one CASE each, producing '<rule_name>;' when the row fails
      CASE WHEN t.customer_id IS NULL                                          THEN 'customer_id_not_null;'  ELSE '' END
    + CASE WHEN t.email IS NULL OR t.email NOT LIKE '%_@_%._%'                 THEN 'email_format;'          ELSE '' END
    + CASE WHEN LEN(t.country) > 2                                             THEN 'country_max_length;'    ELSE '' END
    + CASE WHEN t.signup_date IS NULL AND t.signup_date_raw IS NOT NULL        THEN 'signup_date_valid;'     ELSE '' END
      AS _dq_failures
FROM typed AS t;
GO

-- Block 2: drop the previous external table (metadata only; old Parquet files stay as history)
IF EXISTS (SELECT 1 FROM sys.external_tables WHERE name = 'customers' AND schema_id = SCHEMA_ID('silver'))
    DROP EXTERNAL TABLE silver.customers;
GO

-- Block 3: clean rows, one per business key (latest ingest wins; ties broken by row hash)
CREATE EXTERNAL TABLE silver.customers
WITH (
    LOCATION    = 'silver/customers/run_id={{run_id}}/',
    DATA_SOURCE = ds_curated,
    FILE_FORMAT = ff_parquet
)
AS
WITH hashed AS (
    SELECT
        c.*,
        CONVERT(VARCHAR(64), HASHBYTES('SHA2_256',
            CONCAT_WS('|', c.customer_id, c.first_name, c.last_name, c.email, c.country, c.signup_date)), 2) AS _row_hash
    FROM silver.customers_checked AS c
    WHERE c._dq_failures = ''
),
ranked AS (
    SELECT h.*, ROW_NUMBER() OVER (PARTITION BY h.customer_id ORDER BY h._ingest_date DESC, h._row_hash DESC) AS _rn
    FROM hashed AS h
)
SELECT
    customer_id,
    first_name,
    last_name,
    email,
    country,
    signup_date,
    _row_hash,
    _source_file,
    _ingest_date,
    CAST('{{run_id}}' AS VARCHAR(64)) AS _batch_id,
    SYSUTCDATETIME()                  AS _processed_ts
FROM ranked
WHERE _rn = 1;
GO

-- Block 4: drop the previous rejects table
IF EXISTS (SELECT 1 FROM sys.external_tables WHERE name = 'customers_rejects' AND schema_id = SCHEMA_ID('silver'))
    DROP EXTERNAL TABLE silver.customers_rejects;
GO

-- Block 5: rejects = rows that failed at least one reject rule (all columns kept for investigation)
CREATE EXTERNAL TABLE silver.customers_rejects
WITH (
    LOCATION    = 'silver/customers_rejects/run_id={{run_id}}/',
    DATA_SOURCE = ds_curated,
    FILE_FORMAT = ff_parquet
)
AS
SELECT
    c.*,
    CAST('{{run_id}}' AS VARCHAR(64)) AS _batch_id,
    SYSUTCDATETIME()                  AS _processed_ts
FROM silver.customers_checked AS c
WHERE c._dq_failures <> '';
