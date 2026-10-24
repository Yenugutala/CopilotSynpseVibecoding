---
agent: agent
description: "Generate bronze/silver/gold SQL + the Synapse pipeline from the specs, then open a PR"
---

# Generate the Synapse pipeline from specs

Generate all the code for these source specs: **${input:tables:table names from specs/sources, or 'all'}**
and these model specs: **${input:models:model names from specs/models, 'all', or 'none'}**.

Follow [copilot-instructions.md](../copilot-instructions.md) and these skills:
- [synapse-serverless-sql](../skills/synapse-serverless-sql/SKILL.md)
- [data-quality](../skills/data-quality/SKILL.md)
- [synapse-pipeline](../skills/synapse-pipeline/SKILL.md)
- [git-pr-workflow](../skills/git-pr-workflow/SKILL.md)

## Steps. Do them in order and don't skip any.
1. **Read** `config/environment.yaml`, the requested `specs/sources/*.yaml` and `specs/models/*.yaml`, and every file in `.github/skills/synapse-serverless-sql/references/`.
2. **Plan:** list the files you'll create or change, in a table (file, from which spec, purpose, new or changed).
   - **Scope:** only create or change files for the requested tables and models. Leave the SQL files of every other table as they are.
   - **Naming:** `sql/<layer>/NN_<table>.sql`, where `<table>` is the spec's `table:` value. If a file for that table already exists, update it in place and keep its number.
   - **Numbering a new file:** use the next free `NN` in that layer (for example `03_` after `01_suppliers.sql` and `02_products.sql`). If it references a table with a higher number, say so in the plan and propose a renumbering. Don't renumber anything without my OK.
3. **Setup:** if `sql/00_setup/01_database.sql` or `02_objects.sql` is missing, copy it from the references without changes.
4. **Bronze:** for each source spec, write `sql/bronze/NN_<table>.sql`.
5. **Silver:** for each source spec, write `sql/silver/NN_<table>.sql` with the 5-batch pattern and one `CASE` per DQ rule.
6. **Gold:** for each model spec, write `sql/gold/NN_<model>.sql`.
7. **Build:** run `./tools/build.sh validate`, then `./tools/build.sh build`, then `./tools/build.sh check`.
   - If any of them fail, read the error, fix the SQL (or tell me if the spec is wrong), and run all three again, up to 3 rounds.
   - Never edit `synapse/` JSON. Never run `pip` or install anything.
8. **Self-review** against [review-pipeline.prompt.md](review-pipeline.prompt.md) and fix anything it finds.
9. **Ship** with the git-pr-workflow skill: branch `feat/<use_case>-pipeline`. Show me the staged file list and wait for my OK, then commit, push and open the PR.
10. **Report back** with:
    - the PR link, or the compare URL
    - the files I must upload to the `landing` container (from `source_file`)
    - the steps in Synapse Studio: switch to `main` → Publish → Trigger now → query `gold.<model>`
