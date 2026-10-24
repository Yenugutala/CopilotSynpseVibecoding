---
name: git-pr-workflow
description: Create a feature branch, commit generated code, push to GitHub and open a pull request — never committing to main. Use when generated changes are ready to ship.
---

# Git and PR workflow

## Rules
- **Never commit or push to `main`.** If the current branch is `main`, create a branch first.
- Branch name: `feat/<use_case>-<short-desc>`, for example `feat/<use_case>-pipeline`, or `fix/<use_case>-<short-desc>` for fixes.
- Commit messages follow Conventional Commits: `feat(silver): add <table> CETAS with DQ rules`.
- Only commit files under `sql/`, `synapse/`, `specs/`, `docs/`, `.github/`, `tools/` and `config/`. Never commit `.env*`, data files outside `data/sample/`, or anything with a key in it.

## Procedure (run in the VS Code terminal)
1. Make sure the build is clean:
   ```bash
   ./tools/build.sh validate && ./tools/build.sh check
   ```
2. Create or switch to the branch:
   ```bash
   git switch -c feat/<use_case>-<short-desc>    # or: git switch <existing-branch>
   ```
3. Stage and review:
   ```bash
   git add sql synapse specs docs
   git status --short
   git diff --cached --stat
   ```
   Show the staged file list to the human and wait for them to say OK.
4. Commit and push:
   ```bash
   git commit -m "feat(<layer>): <what changed>"
   git push -u origin HEAD
   ```
5. Write the PR body to `.git/PR_BODY.md`, which is never committed, by filling in every section of [.github/pull_request_template.md](../../pull_request_template.md):
   - what changed
   - which files to upload to `landing/`
   - the DQ test queries
   - the steps to Publish and Trigger in Synapse
6. Open the PR. If `gh` is installed and logged in:
   ```bash
   gh pr create --base main --title "feat(<layer>): <what changed>" --body-file .git/PR_BODY.md
   ```
   Otherwise, give the human the compare URL printed by `git push` and the contents of `.git/PR_BODY.md` to paste into GitHub.

## If something goes wrong
- Push rejected because `main` is protected: you are on `main`. Create a branch (step 2) and push again.
- Authentication failed: ask the human to run `gh auth login`, or to sign in to GitHub in VS Code.
- CI fails on `check`: run `./tools/build.sh build`, commit the regenerated `synapse/` files, and push again.
