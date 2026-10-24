---
applyTo: "specs/**/*.yaml"
description: "Rules for source and model spec files"
---

# Spec rules

Specs are the contract between the business and the generated code. Keep them small, explicit and reviewed.

## Source specs: `specs/sources/<table>.yaml`
Required keys: `table`, `description`, `source_file`, `format`, `business_key`, `columns`, `dq_rules`.
- `table`: snake_case, and the same as the file name.
- `source_file`: exact CSV name expected in the `landing` container.
- `columns[]`: `name` (snake_case), `type`, `nullable`, `description` (all required). Order must match the CSV header.
- Allowed `type`: `INT`, `BIGINT`, `SMALLINT`, `BIT`, `DATE`, `DATETIME2`, `VARCHAR(n)`, `DECIMAL(p,s)`.
- `dq_rules[]`: `name`, `column`, `check`, `action` (`reject` or `warn`), plus any parameters the check needs.
  - `check` is one of: `not_null`, `regex` (`pattern`, a T-SQL LIKE pattern), `valid_type`, `max_length` (`value`), `min_value` (`value`), `allowed_values` (`values`), `references` (`ref_table`, `ref_column`), `unique`.

## Model specs: `specs/models/<model>.yaml`
Required keys: `model`, `layer: gold`, `description`, `grain`, `sources`, `join`, `columns`.
- `sources` must name existing `silver.<table>` tables.
- Every `columns[]` entry has `name`, `expression` and `description`.

## Process
- Templates: `specs/_templates/source_spec.template.yaml` and `model_spec.template.yaml`.
- To add a source, use `/add-new-source`. It drafts the spec from a CSV sample in `data/sample/` for a human to review.
- To add a gold model, use `/add-new-model`. It drafts the spec from a plain-English requirement.
- Run `./tools/build.sh validate` after every spec change.
- Never put sample data values, personal data or secrets in a spec.
