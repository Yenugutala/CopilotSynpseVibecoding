---
agent: agent
description: "Demo: generate every spec, all SQL and the Synapse pipeline in one run, then commit on the current local branch (no push)"
---

# Generate everything (demo mode)

Run the whole flow in one go. **Don't stop to ask for review between steps.** Only stop if a step fails three times in a row.

Rules for this run:
- Follow [copilot-instructions.md](../copilot-instructions.md).
- Run Python only through `./tools/build.sh`. Never install anything.
- Stay on the **current branch**. Never create a branch, never switch branches, never commit to `main`.

## Step 1: Source specs
For **every** CSV file in `data/sample/`, follow the steps in [add-new-source.prompt.md](add-new-source.prompt.md) and write `specs/sources/<table>.yaml`. Skip step 7 of that prompt (the reply to me).

## Step 2: Model specs
Read [demo/model_requirements.md](../../demo/model_requirements.md). For **each** `##` section, follow the steps in [add-new-model.prompt.md](add-new-model.prompt.md):
- The heading is the model name.
- The text under it is the requirement.

Write `specs/models/<model>.yaml`. Skip the final reply step.

## Step 3: SQL and pipeline
Follow steps 1–8 of [generate-pipeline.prompt.md](generate-pipeline.prompt.md) with `tables=all` and `models=all`. Show the plan table, but **don't wait for my OK**.

## Step 4: Commit locally (don't push)
1. Check that the current branch isn't `main` (`git branch --show-current`). If it is `main`, stop and tell me.
2. Run:
   ```
   git add specs sql synapse
   git commit -m "feat: generate specs, SQL and Synapse pipeline with Copilot"
   ```
3. **Don't run `git push`.** I'll push and open the PR myself.

## Step 5: Report
Reply with a short summary:
- One table listing every file created: path, and the spec it came from.
- The bad sample rows that the DQ rules will reject.
- The local branch name, and the command to push it when I'm ready: `git push -u origin HEAD`.
- The next steps:
  1. push the branch, open the PR to `main` and merge it
  2. upload `data/sample/*.csv` to the `landing` container
  3. in Synapse Studio: refresh, then Publish, then Trigger now
  4. query `gold.<model>`
