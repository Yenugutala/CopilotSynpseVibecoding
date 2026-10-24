# AGENTS.md

Instructions for any AI coding agent working in this repo (GitHub Copilot, Claude Code, Cursor and others).

The full rules are in [.github/copilot-instructions.md](.github/copilot-instructions.md). Read it first. The skills in [.github/skills/](.github/skills/) hold the patterns.

## Summary
- **Goal:** generate Azure Synapse **serverless SQL** + a Synapse **pipeline** from the YAML specs in `specs/`.
- **Flow:** `specs/` → `sql/<layer>/*.sql` → `./tools/build.sh build` → `synapse/` JSON → PR.
- **Never:** commit to `main`, hand-edit `synapse/**/*.json`, put secrets in code, touch data in storage, or use MERGE/UPDATE/DELETE/INSERT.
- **Always:** re-runnable SQL, `{{placeholders}}` for environment values, snake_case names, `_`-prefixed metadata columns.

## Commands
```bash
./tools/build.sh validate   # specs + SQL conventions
./tools/build.sh build      # regenerate synapse/ JSON
./tools/build.sh check      # what CI runs
```
