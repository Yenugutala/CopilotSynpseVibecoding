-- Reference pattern: sql/bronze/NN_<table>.sql
-- Worked example for a hypothetical spec specs/sources/products.yaml (NOT a real spec in this repo):
--   columns: product_id INT, product_code VARCHAR(20), product_name VARCHAR(150), category VARCHAR(50),
--            unit_price DECIMAL(10,2), stock_qty INT, status VARCHAR(20), supplier_id INT, launch_date DATE
--   source_file: products.csv
-- Bronze = schema-on-read view over every raw file ever loaded. All columns VARCHAR, no cleaning.
-- filepath(1) returns the value matched by the first * (the ingest date folder).
CREATE OR ALTER VIEW bronze.products AS
SELECT
    r.product_id,
    r.product_code,
    r.product_name,
    r.category,
    r.unit_price,
    r.stock_qty,
    r.status,
    r.supplier_id,
    r.launch_date,
    r.filename()                AS _source_file,
    CAST(r.filepath(1) AS DATE) AS _ingest_date
FROM OPENROWSET(
        BULK 'products/ingest_date=*/products.csv',
        DATA_SOURCE = 'ds_raw',
        FORMAT = 'CSV',
        PARSER_VERSION = '2.0',
        HEADER_ROW = TRUE,
        FIELDTERMINATOR = ','
     )
     WITH (
        product_id    VARCHAR(50),
        product_code  VARCHAR(50),
        product_name  VARCHAR(150),
        category      VARCHAR(50),
        unit_price    VARCHAR(50),
        stock_qty     VARCHAR(50),
        status        VARCHAR(50),
        supplier_id   VARCHAR(50),
        launch_date   VARCHAR(50)
     ) AS r;
