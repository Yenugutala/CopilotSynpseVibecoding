---
applyTo: "docs/**/*.md,README.md,CONTRIBUTING.md"
description: "Documentation style for this repo"
---

# Documentation rules

- Write for a new teammate who knows SQL but not this repo.
- Numbered steps for procedures, tables for settings, and fenced code blocks for commands.
- Use the real names from `config/environment.yaml`. Never include keys, passwords or tokens.
- Diagrams use Mermaid (`flowchart`) so they render on GitHub.
- When a change affects the flow (new layer, new activity, new setup step), update `docs/architecture.md` in the same PR.
