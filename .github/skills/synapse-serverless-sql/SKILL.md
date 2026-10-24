---
name: synapse-serverless-sql
description: Write T-SQL for Azure Synapse serverless SQL pool — OPENROWSET bronze views over CSV, CETAS silver Parquet tables with DQ and de-duplication, gold views. Use when generating or fixing any file in sql/.
---

# Synapse serverless SQL

## When to use
Generating or editing `sql/00_setup`, `sql/bronze`, `sql/silver` or `sql/gold` from the specs.

## Reference files (copy these patterns)
| Target file | Reference |
|---|---|
| `sql/00_setup/01_database.sql` | [references/00_setup_01_database.sql](references/00_setup_01_database.sql) |
| `sql/00_setup/02_objects.sql` | [references/00_setup_02_objects.sql](references/00_setup_02_objects.sql) |
| `sql/bronze/NN_<table>.sql` | [references/bronze_02_products.sql](references/bronze_02_products.sql) |
| `sql/silver/NN_<table>.sql` | [references/silver_02_products.sql](references/silver_02_products.sql) |
| `sql/gold/NN_<model>.sql` | [references/gold_01_supplier_product_summary.sql](references/gold_01_supplier_product_summary.sql) |

The setup files are the same for every use case, so copy them as they are. The bronze, silver and gold references are worked examples for **hypothetical** `products`, `suppliers` and `supplier_product_summary` specs. Copy the **patterns**, never the table or column names. Every name comes from your spec.

## Procedure for one source spec
1. Read `specs/sources/<table>.yaml`.
2. **Bronze:** list every column in the `WITH (...)` clause as `VARCHAR(50)`, or `VARCHAR(n)` when the spec says `VARCHAR(n)` (use a larger n for free text). Keep the CSV column order. `BULK` path: `'<table>/ingest_date=*/<source_file>'`.
3. **Silver** (5 batches separated by `GO`):
   1. `CREATE OR ALTER VIEW silver.<table>_checked`: a `typed` CTE with `TRY_CAST(NULLIF(LTRIM(RTRIM(col)),'') AS <spec type>)`. Lowercase emails, uppercase codes. Keep `<col>_raw` for every column that has a `valid_type` rule. Then `_dq_failures` built from one `CASE` per **reject** rule. See the data-quality skill.
   2. `IF EXISTS ... DROP EXTERNAL TABLE silver.<table>`
   3. CETAS `silver.<table>` into `LOCATION = 'silver/<table>/run_id={{run_id}}/'`, keeping rows where `_dq_failures = ''`. Add `_row_hash` (SHA2_256 over all data columns joined with `CONCAT_WS('|', ...)`), then `ROW_NUMBER() OVER (PARTITION BY <business_key> ORDER BY _ingest_date DESC, _row_hash DESC)` and keep `_rn = 1`. Add `_batch_id = '{{run_id}}'` and `_processed_ts = SYSUTCDATETIME()`.
   4. `IF EXISTS ... DROP EXTERNAL TABLE silver.<table>_rejects`
   5. CETAS `silver.<table>_rejects` into `'silver/<table>_rejects/run_id={{run_id}}/'` with the rows where `_dq_failures <> ''`.
4. **Warn** rules don't reject anything. Add a `_dq_warnings` column to the clean CETAS, built the same way as `_dq_failures`.

## Procedure for one model spec
`CREATE OR ALTER VIEW gold.<model>` with the spec's columns in order, named exactly as the spec says. Use `COALESCE` for sums and counts so left-side rows without matches show 0. Put the spec `filters` for the right-hand table of a LEFT JOIN in the `ON` clause.

## Serverless pitfalls (these cause real failures)
| Pitfall | Do this |
|---|---|
| CETAS fails when the target folder already has files | Always write to `.../run_id={{run_id}}/` (a new folder each run) |
| `CREATE VIEW must be the only statement in the batch` | `GO` before and after every `CREATE OR ALTER VIEW` |
| `CREATE SCHEMA` inside `IF` fails | `IF NOT EXISTS (...) EXEC('CREATE SCHEMA x')` |
| `CREATE DATABASE` must run in master | First line `-- target_db: master` |
| Collation / UTF-8 warnings on CSV | The database is created with `Latin1_General_100_BIN2_UTF8` |
| Empty CSV fields come through as `''` | `NULLIF(LTRIM(RTRIM(col)),'')` before every cast |
| Bad dates or numbers stop the query | Always `TRY_CAST`, never `CAST`, on raw values |
| `DROP EXTERNAL TABLE` leaves the files | That's expected. Old `run_id` folders are history (pennies of storage). |
| Silver table B joins silver table A | Number the files so A builds first (`01_suppliers`, `02_products`) |
| `MERGE`/`UPDATE`/`DELETE`/`INSERT` not supported | Rebuild with CETAS instead |
| Access denied reading storage | No credential in SQL. The workspace identity needs *Storage Blob Data Contributor* (see docs/setup). |
