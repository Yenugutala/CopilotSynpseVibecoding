-- Generated from specs/sources/customers.yaml
-- Bronze = schema-on-read view over every raw file ever loaded. All columns VARCHAR, no cleaning.
-- Columns are at least VARCHAR(50) so a bad value never breaks the read; silver rejects it instead.
CREATE OR ALTER VIEW bronze.customers AS
SELECT
    r.customer_id,
    r.first_name,
    r.last_name,
    r.email,
    r.country,
    r.signup_date,
    r.filename()                AS _source_file,
    CAST(r.filepath(1) AS DATE) AS _ingest_date
FROM OPENROWSET(
        BULK 'customers/ingest_date=*/customers.csv',
        DATA_SOURCE = 'ds_raw',
        FORMAT = 'CSV',
        PARSER_VERSION = '2.0',
        HEADER_ROW = TRUE,
        FIELDTERMINATOR = ','
     )
     WITH (
        customer_id  VARCHAR(50),
        first_name   VARCHAR(100),
        last_name    VARCHAR(100),
        email        VARCHAR(255),
        country      VARCHAR(50),
        signup_date  VARCHAR(50)
     ) AS r;
