# AGENTS.md

Instructions for any AI coding agent working in this repo (GitHub Copilot, Claude Code, Cursor and others).

The full rules are in [.github/copilot-instructions.md](.github/copilot-instructions.md). Read it first. The skills in [.github/skills/](.github/skills/) hold the patterns.

## Summary
- **Goal:** generate Azure Synapse **serverless SQL** + a Synapse **pipeline** from the YAML specs in `specs/`.
- **Flow:** `specs/` → `sql/<layer>/*.sql` → `python3 tools/build_synapse.py build` → `synapse/` JSON → PR.
- **Never:** commit to `main`, hand-edit `synapse/**/*.json`, put secrets in code, touch data in storage, or use MERGE/UPDATE/DELETE/INSERT.
- **Always:** re-runnable SQL, `{{placeholders}}` for environment values, snake_case names, `_`-prefixed metadata columns.

## Commands
```bash
python3 tools/build_synapse.py validate   # specs + SQL conventions
python3 tools/build_synapse.py build      # regenerate synapse/ JSON
python3 tools/build_synapse.py check      # what CI runs
```
