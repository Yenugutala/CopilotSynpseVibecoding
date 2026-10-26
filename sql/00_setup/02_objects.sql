-- Reference pattern: sql/00_setup/02_objects.sql
-- Schemas, external data sources and file formats. Every statement is guarded, so re-runs are safe.
-- No DATABASE SCOPED CREDENTIAL: storage is accessed with the caller's Entra identity
-- (workspace managed identity when the pipeline runs, your own identity when you query).
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'bronze') EXEC('CREATE SCHEMA bronze');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'silver') EXEC('CREATE SCHEMA silver');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'gold')   EXEC('CREATE SCHEMA gold');
GO

IF NOT EXISTS (SELECT 1 FROM sys.external_data_sources WHERE name = 'ds_raw')
    CREATE EXTERNAL DATA SOURCE ds_raw
    WITH (LOCATION = 'https://{{storage_account}}.dfs.core.windows.net/{{raw_container}}');

IF NOT EXISTS (SELECT 1 FROM sys.external_data_sources WHERE name = 'ds_curated')
    CREATE EXTERNAL DATA SOURCE ds_curated
    WITH (LOCATION = 'https://{{storage_account}}.dfs.core.windows.net/{{curated_container}}');

IF NOT EXISTS (SELECT 1 FROM sys.external_file_formats WHERE name = 'ff_parquet')
    CREATE EXTERNAL FILE FORMAT ff_parquet
    WITH (FORMAT_TYPE = PARQUET, DATA_COMPRESSION = 'org.apache.hadoop.io.compress.SnappyCodec');
