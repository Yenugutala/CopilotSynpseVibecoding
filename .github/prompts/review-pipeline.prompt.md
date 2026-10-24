---
agent: ask
description: "Review generated SQL and pipeline against the repo rules (read-only)"
---

# Review the generated pipeline

Review the files in `sql/` and `synapse/` (or the current branch diff) against [copilot-instructions.md](../copilot-instructions.md), [synapse-sql.instructions.md](../instructions/synapse-sql.instructions.md) and the specs. **Don't change any files.**

Check every item and report each one as PASS or FAIL, with the file and line:
1. Every source spec has bronze + silver (clean and rejects) SQL, and every model spec has a gold view.
2. Columns, types and order match the specs exactly. Nothing is invented or missing.
3. Every `dq_rules` entry has exactly one `CASE`. Reject rules go to `_dq_failures`, warn rules to `_dq_warnings`.
4. Silver de-duplicates on the spec's `business_key`.
5. No MERGE, UPDATE, DELETE, INSERT, CREDENTIAL, SECRET, SAS, or hard-coded account, container or database names.
6. Every CETAS `LOCATION` contains `run_id={{run_id}}`, and is preceded by a guarded `DROP EXTERNAL TABLE`.
7. `GO` separates every `CREATE OR ALTER VIEW` and every CETAS.
8. File numbering builds referenced tables first.
9. `./tools/build.sh check` passes. If you can't run it, say so.
10. Gold views list explicit columns (no `SELECT *`), and LEFT JOIN filters are in the `ON` clause.

End with a short list of fixes in priority order.
