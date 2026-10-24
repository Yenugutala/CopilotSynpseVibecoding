-- Generated from specs/sources/orders.yaml
-- Bronze = schema-on-read view over every raw file ever loaded. All columns VARCHAR, no cleaning.
-- Columns are at least VARCHAR(50) so a bad value never breaks the read; silver rejects it instead.
CREATE OR ALTER VIEW bronze.orders AS
SELECT
    r.order_id,
    r.customer_id,
    r.order_date,
    r.product,
    r.quantity,
    r.unit_price,
    r.status,
    r.filename()                AS _source_file,
    CAST(r.filepath(1) AS DATE) AS _ingest_date
FROM OPENROWSET(
        BULK 'orders/ingest_date=*/orders.csv',
        DATA_SOURCE = 'ds_raw',
        FORMAT = 'CSV',
        PARSER_VERSION = '2.0',
        HEADER_ROW = TRUE,
        FIELDTERMINATOR = ','
     )
     WITH (
        order_id     VARCHAR(50),
        customer_id  VARCHAR(50),
        order_date   VARCHAR(50),
        product      VARCHAR(100),
        quantity     VARCHAR(50),
        unit_price   VARCHAR(50),
        status       VARCHAR(50)
     ) AS r;
