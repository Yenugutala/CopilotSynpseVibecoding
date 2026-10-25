# Demo scripts

| Script | What it does |
|---|---|
| `./demo/generate.sh` | Sends one prompt ([generate-all](../.github/prompts/generate-all.prompt.md)) to Copilot in VS Code. Copilot then writes every spec (one per CSV in `data/sample/`, plus the models in [model_requirements.md](model_requirements.md)), all the SQL and the Synapse pipeline, runs the build checks, then **commits on your current local branch**. Nothing is pushed. It refuses to run on `main`. |
| `./demo/revert.sh` | Deletes everything Copilot generated (specs, SQL, the pipeline JSON), so you can run the demo again. Add `--commit` to commit the removal on the current local branch (it refuses on `main`, and never pushes). |

## Demo run
1. Open **only** this folder in VS Code (`code ~/Desktop/GithubCopilot_coding`).
2. In Chat, select **Local · Agent** and your model (for example Claude Sonnet 5.5).
3. In the VS Code terminal, run `git switch -c demo/customer-orders` (any non-main branch), then `./demo/generate.sh`. Click **Allow** / **Keep** as Copilot works.
4. When you're happy, run `git push -u origin HEAD`, then open the PR to `main` and merge it.
5. Upload `data/sample/*.csv` to the `landing` container.
6. In Synapse Studio: refresh → **Publish** → **Trigger now** → query `gold.customer_order_summary`.

## Reset after the demo
```bash
git switch main && git pull
git switch -c chore/demo-reset
./demo/revert.sh --commit    # then: git push -u origin HEAD, open a PR to main and merge it
```
After merging, **Publish** in Synapse Studio removes the pipeline from live too. The data in `landing`/`raw`/`curated` isn't touched. Delete it in the portal if you want a fully clean storage account.
