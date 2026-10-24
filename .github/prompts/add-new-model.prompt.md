---
agent: agent
description: "Create a gold model spec (specs/models/<model>.yaml) from a plain-English description"
---

# Add a new gold model spec

What the report or view should show: **${input:requirement:describe the grain, measures, filters and which rows must be kept}**

Follow [specs.instructions.md](../instructions/specs.instructions.md). Use [specs/_templates/model_spec.template.yaml](../../specs/_templates/model_spec.template.yaml) as the exact format.

1. Read every `specs/sources/*.yaml`. Use **only** columns that exist there. If the requirement needs a column that no spec has, stop and tell me.
2. Choose the snake_case `model` name, the `grain`, the `sources`, the `join` type and any `filters`:
   - Use a LEFT JOIN when rows without matches must be kept (for example suppliers with no products).
3. List the output `columns` with an `expression` and a `description` for each:
   - Aggregates need a defined result when there's no match (for example 0 instead of NULL). Say so in the description.
4. Write `specs/models/<model>.yaml` using every key from the template, in the same order: `model`, `layer: gold`, `description`, `grain`, `sources`, `join`, `filters` (optional), `columns`.
5. Run `./tools/build.sh validate`. If it reports errors, fix the spec and run it again, up to 3 times. Never install anything. If it still fails, show me the errors.
6. Show me the spec, and point out every assumption you made (join type, filters, how NULLs are handled). **Don't generate SQL.** After I review the spec, I'll run `/generate-pipeline`.
