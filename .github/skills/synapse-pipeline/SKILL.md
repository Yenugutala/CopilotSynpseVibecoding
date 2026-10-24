---
name: synapse-pipeline
description: Build and ship the Synapse pipeline (landing -> raw -> curated) from SQL and specs using tools/build_synapse.py, and explain how it reaches Synapse Studio through Git. Use after SQL changes, when synapse/ JSON is stale, or when a pipeline run fails.
---

# Synapse pipeline

## What gets generated
`./tools/build.sh build` writes these files. Never edit them by hand.

| File | Purpose |
|---|---|
| `synapse/linkedService/ls_adls.json` | ADLS Gen2 `https://<account>.dfs.core.windows.net/` with managed identity |
| `synapse/linkedService/ls_serverless_sql.json` | Serverless endpoint, `DBName` parameter, managed identity |
| `synapse/dataset/ds_adls_binary.json` | Any file by `container` / `folder` / `file` (folder must be non-empty) |
| `synapse/dataset/ds_adls_binary_root.json` | A file at the container root by `container` / `file`. Used for `landing/` sources, because Synapse rejects an empty folder value. |
| `synapse/pipeline/pl_<use_case>.json` | The pipeline |
| `synapse/integrationRuntime/AutoResolveIntegrationRuntime.json` | Default Azure IR |

## Pipeline shape
```
copy_<table>_landing_to_raw   (one per specs/sources/*.yaml, run in parallel)
   landing/<source_file>  ->  raw/<table>/ingest_date=<trigger date>/<source_file>
        │ all copies succeed
        ▼
00_setup_01_database (master) -> 00_setup_02_objects -> bronze_NN_* -> silver_NN_* -> gold_NN_*
```
- Each SQL file becomes one **Script** activity, and every `GO` block becomes a separate script inside it.
- Script activities run one after another, in folder order and then file-name order.

## Procedure after SQL or spec changes
1. `./tools/build.sh validate`: fix every error it reports.
2. `./tools/build.sh build`
3. `./tools/build.sh check` should print `synapse/ is up to date.`
4. Review `git diff synapse/`. The changes should match the SQL you changed.
5. Ship with the git-pr-workflow skill.

## How it reaches Synapse (humans do these steps)
1. The PR is merged to `main` (the collaboration branch).
2. In Synapse Studio (Git mode, root folder `/synapse`), switch to branch `main`. The pipeline appears under **Integrate → Pipelines → copilot-generated**.
3. Click **Publish**. This makes it live and writes to the `workspace_publish` branch.
4. Upload the CSVs to `landing/`, then open the pipeline → **Add trigger → Trigger now**.
5. Watch **Monitor → Pipeline runs**, then query `SELECT TOP 100 * FROM gold.<model>` on Built-in.

## Troubleshooting a failed run
Ask the human for the failed activity name and its error message (**Monitor → run → activity → error icon**). Don't guess the cause.

| Error contains | Likely cause | Fix |
|---|---|---|
| `Login failed` / `principal ... is not able to access` on a Script activity | The workspace identity has no serverless login | One-time grant in `docs/setup/04-synapse-git-and-permissions.md` |
| `403` / `AuthorizationPermissionMismatch` on Copy or OPENROWSET | Missing *Storage Blob Data Contributor* | Assign the role to the workspace managed identity on the storage account |
| `PathNotFound` on copy | The file isn't in `landing/`, or its name differs from `source_file` | Upload the file with the exact name in the spec |
| `CREATE VIEW must be the only statement` | Missing `GO` | Add `GO` around the view, then rebuild |
| `already exists` on CETAS | The location was reused | Make sure the LOCATION contains `run_id={{run_id}}` |
| `Error converting data type` | `CAST` used on raw data | Use `TRY_CAST` and a DQ rule |
