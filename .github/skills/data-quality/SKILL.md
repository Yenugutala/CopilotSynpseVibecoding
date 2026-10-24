---
name: data-quality
description: Translate dq_rules from specs/sources/*.yaml into T-SQL CASE expressions for the silver _dq_failures / _dq_warnings columns, and write DQ test queries. Use when generating silver SQL or adding a DQ rule.
---

# Data quality rules → SQL

Every rule becomes one `CASE` expression in `silver.<table>_checked`. They are joined with `+`, and each one produces `'<rule_name>;'` when the row fails, or `''` when it passes.
- `action: reject` rules go into `_dq_failures`. Failing rows go to `silver.<table>_rejects`.
- `action: warn` rules go into `_dq_warnings`. Failing rows stay in silver and are only flagged.

`t` is the `typed` CTE: values already trimmed and cast with `TRY_CAST`.

| `check` | Spec parameters | SQL (fails when TRUE) |
|---|---|---|
| `not_null` | — | `t.<col> IS NULL` |
| `regex` | `pattern` (T-SQL LIKE) | `t.<col> IS NULL OR t.<col> NOT LIKE '<pattern>'` |
| `valid_type` | — | `t.<col> IS NULL AND t.<col>_raw IS NOT NULL` (the raw value existed but couldn't be cast) |
| `max_length` | `value` | `LEN(t.<col>) > <value>` |
| `min_value` | `value` | `t.<col> < <value>` |
| `allowed_values` | `values` | `t.<col> IS NULL OR t.<col> NOT IN ('A','B',...)` |
| `references` | `ref_table`, `ref_column` | `NOT EXISTS (SELECT 1 FROM silver.<ref_table> AS r WHERE r.<ref_column> = t.<col>)` |
| `unique` | — | Handled by de-duplication on `business_key`. Report duplicates with the test query below. |

Template:
```sql
      CASE WHEN <fail condition> THEN '<rule_name>;' ELSE '' END
    + CASE WHEN <fail condition> THEN '<rule_name>;' ELSE '' END
      AS _dq_failures
```

## Notes
- `valid_type` needs `<col>_raw` in the typed CTE: `NULLIF(LTRIM(RTRIM(<col>)),'') AS <col>_raw`.
- `references` must point to a silver table built in an **earlier** file (lower `NN`).
- A rule that needs a parameter missing from the spec is a spec error. Stop and ask.

## DQ test queries (humans run these after the pipeline)
Put them in the PR description so reviewers can run them in Synapse Studio:
```sql
-- reject counts by rule
SELECT value AS rule_name, COUNT(*) AS rows_failed
FROM silver.<table>_rejects CROSS APPLY STRING_SPLIT(_dq_failures, ';')
WHERE value <> '' GROUP BY value;

-- the business key is unique in silver (expect 0 rows)
SELECT <business_key>, COUNT(*) FROM silver.<table> GROUP BY <business_key> HAVING COUNT(*) > 1;

-- reconciliation: bronze rows = silver + rejects + duplicates removed
SELECT (SELECT COUNT(*) FROM bronze.<table>)            AS bronze_rows,
       (SELECT COUNT(*) FROM silver.<table>)            AS silver_rows,
       (SELECT COUNT(*) FROM silver.<table>_rejects)    AS rejected_rows;
```
