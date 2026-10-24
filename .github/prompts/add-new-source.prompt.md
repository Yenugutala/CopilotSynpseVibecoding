---
agent: agent
description: "Create a source spec (specs/sources/<table>.yaml) from a sample CSV"
---

# Add a new source spec

Sample CSV: **${input:csv_path:data/sample/<file>.csv}**

Read these three files first. They define the exact format:
- [specs.instructions.md](../instructions/specs.instructions.md): the rules
- [source_spec.template.yaml](../../specs/_templates/source_spec.template.yaml): every key, in the right order
- [example_source_spec.yaml](../../specs/_templates/example_source_spec.yaml): a filled-in example. Copy its **style**, never its names.

## Steps
1. Read the CSV header and the first 20 rows with your file-read tool. Don't read the whole file.
2. Write `specs/sources/<table>.yaml`, where `<table>` is the CSV file name in snake_case. Use **every** top-level key from the template, in the same order:
   `table`, `description`, `source_file` (the CSV file name), `format`, `business_key`, `columns`, `dq_rules`.
3. **Columns:** one entry per CSV column, in header order, each with `name`, `type`, `nullable` and `description`.
   - `type` must be one of: `INT`, `BIGINT`, `SMALLINT`, `BIT`, `DATE`, `DATETIME2`, `VARCHAR(n)`, `DECIMAL(p,s)`.
     - Never use `integer`, `string`, `float`, `number`, `text` or `date-time`.
     - Money and prices are `DECIMAL(10,2)`. Codes and short text are `VARCHAR(n)`, with n a little above the longest valid value.
   - Business-key columns are **always** `nullable: false`. An empty key in the sample is a bad row, and gets a `not_null` rule.
   - For other columns, `nullable: true` only if empty values look legitimate.
   - `description` is one plain sentence. Write open questions as `TODO confirm …`, with no colon after TODO. Put any value that contains `: ` or `#` in double quotes.
4. **business_key:** the column(s) that uniquely identify a row. Say why you chose them.
5. **dq_rules:** every rule has `name` (`<column>_<check>`), `column`, `check` and `action` (`reject` or `warn`), plus the parameter its check needs.
   | When | Use |
   |---|---|
   | Key or required column | `not_null` |
   | Text that has a format (email, code, phone) | `regex` with a T-SQL LIKE `pattern`. **Never** `valid_type` for this. |
   | Numbers and dates | `valid_type` |
   | Quantities, prices, amounts | `min_value` |
   | Fixed-length codes (country, currency) | `max_length` |
   | A small set of status-like values | `allowed_values` |
   | A column pointing to another spec's key | `references` with `action: warn` |
   - **Bad-looking sample values are data errors, not valid values.** Never add them to `allowed_values`, and never stretch a type or length to fit them. Write a rule that rejects them, and mention them in the summary.
6. Run `./tools/build.sh validate`. If it reports errors, fix the spec and run it again, up to 3 times. Never install anything. If it still fails, show me the errors.
7. Reply with:
   - the final spec
   - the business key, and why you chose it
   - the bad sample rows you noticed, and which rule rejects each one
   - every `TODO confirm` item

   **Don't generate SQL.** I'll run `/generate-pipeline` after I've reviewed the spec.
