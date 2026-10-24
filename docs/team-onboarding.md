# Team onboarding

## Day 1 checklist
- [ ] Access to the GitHub repo (write), the Azure resource group `rg-copilot-demo` (Contributor) and the Synapse workspace (Synapse Contributor or Administrator)
- [ ] *Storage Blob Data Contributor* on `stcopilotdemokk1`, so you can upload to `landing` and query gold
- [ ] VS Code installed in **Applications**, signed in to GitHub Copilot
- [ ] Foundry model added in VS Code: [setup/02](setup/02-azure-ai-foundry-and-copilot.md) section 2.4
- [ ] `brew install gh && gh auth login`, `pip3 install pyyaml`
- [ ] Clone the repo, open it in VS Code, and run `python3 tools/build_synapse.py validate`

## What Copilot knows automatically
| File | Loaded when |
|---|---|
| `.github/copilot-instructions.md` | Every chat in this repo |
| `.github/instructions/*.instructions.md` | You work on files matching their `applyTo` glob |
| `.github/skills/*/SKILL.md` | The task matches the skill description, or a prompt links to it |
| `.github/prompts/*.prompt.md` | You type `/<name>` in Chat |
| `.github/agents/data-engineer.agent.md` | You pick **data-engineer** in the agent dropdown |

## Your first change (about 30 minutes)
1. `git switch -c feat/customer_orders-add-segment`
2. Add a column to `specs/models/customer_order_summary.yaml`, for example `customer_segment` (`CASE WHEN total_revenue > 1000 THEN 'HIGH' ELSE 'STANDARD' END`).
3. Chat (Agent) → `/generate-pipeline` with tables `customers orders` and model `customer_order_summary`.
4. Review → PR → merge → Publish → Trigger now → query.

## Getting help
- Pipeline errors: paste the exact error into Copilot Chat. The synapse-pipeline skill has a troubleshooting table.
- Copilot keeps making the same mistake: tell a platform owner, so the fix goes into a skill or instruction file ([CONTRIBUTING.md](../CONTRIBUTING.md)).
