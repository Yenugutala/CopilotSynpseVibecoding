---
agent: agent
description: "Create a source spec (specs/sources/<table>.yaml) from a sample CSV"
---

# Add a new source spec

Sample CSV: **${input:csv_path:data/sample/<file>.csv}**

Follow [specs.instructions.md](../instructions/specs.instructions.md). Use [specs/_templates/source_spec.template.yaml](../../specs/_templates/source_spec.template.yaml) as the exact format. Keep the key order, and don't leave any `<...>` placeholders.

1. Read the header and the first 20 rows of the CSV. Don't read the whole file.
2. Work out the details for each column:
   - a snake_case name
   - the smallest allowed type that fits every sample value
   - `nullable` (true if any value is empty)
   - a one-line description (mark it `TODO: confirm` if unsure)
3. Propose a `business_key`, and say why you chose it.
4. Propose `dq_rules`:
   - `not_null` on key columns
   - `valid_type` on dates and numbers
   - `allowed_values` for low-cardinality text columns (list the values you saw)
   - `references` where a column clearly points to another spec's key
5. Write `specs/sources/<table>.yaml` and run `python3 tools/build_synapse.py validate`.
6. Show me the spec and list every `TODO: confirm`. **Don't generate SQL.** After I review the spec, I'll run `/generate-pipeline`.
