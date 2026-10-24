---
applyTo: "sql/**/*.sql"
description: "T-SQL rules for Synapse serverless SQL files (setup, bronze, silver, gold)"
---

# Synapse serverless SQL rules

Before writing SQL, read the matching reference in `.github/skills/synapse-serverless-sql/references/` and follow it closely.

## File layout
- One file per table or model: `sql/<layer>/NN_<table_or_model>.sql`.
- The first line of the file is a header comment saying which spec it came from, for example `-- Generated from specs/sources/<table>.yaml`.
- Files under `sql/00_setup/` that must run in `master` start with `-- target_db: master` as the **first line**.
- Put `GO` on its own line between statements that must be in separate batches:
  - `CREATE OR ALTER VIEW` must be the only statement in its batch.
  - `CREATE EXTERNAL TABLE ... AS SELECT` goes in its own batch, after the `DROP EXTERNAL TABLE` batch.

## Placeholders (never hard-code these)
| Placeholder | Becomes |
|---|---|
| `{{database}}` | serverless database name |
| `{{storage_account}}` | ADLS account name |
| `{{raw_container}}` / `{{curated_container}}` / `{{landing_container}}` | container names |
| `{{run_id}}` | pipeline run id (use in CETAS `LOCATION` and `_batch_id`) |
| `{{ingest_date}}` | pipeline trigger date `yyyy-MM-dd` |

- Use placeholders only in SQL code, never in comments.
- Never write `@{` in SQL. It is reserved for pipeline expressions.

## Allowed and forbidden
- Allowed: `OPENROWSET`, `CREATE OR ALTER VIEW`, `CREATE EXTERNAL TABLE ... AS SELECT`, `DROP EXTERNAL TABLE`, `CREATE EXTERNAL DATA SOURCE`, `CREATE EXTERNAL FILE FORMAT`, `CREATE SCHEMA` (through `EXEC`), `TRY_CAST`, `HASHBYTES`, window functions.
- Forbidden: `MERGE`, `UPDATE`, `DELETE`, `INSERT`, `CREATE TABLE` (non-external), `CREDENTIAL`/`SECRET`/`SAS`, `SELECT *` in gold views.

## Per layer
- **bronze**: `CREATE OR ALTER VIEW bronze.<table>` over `OPENROWSET(BULK '<table>/ingest_date=*/<source_file>', DATA_SOURCE='ds_raw', FORMAT='CSV', PARSER_VERSION='2.0', HEADER_ROW=TRUE)`. Every column is `VARCHAR`. Add `r.filename() AS _source_file` and `CAST(r.filepath(1) AS DATE) AS _ingest_date`.
- **silver**: the 5-batch pattern:
  1. `silver.<table>_checked` view (typed + `_dq_failures`)
  2. drop `silver.<table>`
  3. CETAS clean rows de-duplicated on `business_key`
  4. drop `silver.<table>_rejects`
  5. CETAS rejects

  Cast with `TRY_CAST(NULLIF(LTRIM(RTRIM(col)),'') AS <type>)`.
- **gold**: `CREATE OR ALTER VIEW gold.<model>` with explicit columns, exactly as listed in the model spec. Put LEFT JOIN filters in the `ON` clause.

## Style
- Keywords uppercase, identifiers snake_case, 4-space indent, one column per line, table aliases on every column in joins.
