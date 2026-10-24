# 5. GitHub repo + local tools

## 5.1 Create the repo
1. On github.com → **New repository**. Name it, for example, `copilot-synapse-pipelines` (private is fine).
2. Tick **Add a README file** so that `main` exists. Click **Create**.

## 5.2 Protect `main`
**Settings → Rules → Rulesets → New branch ruleset**, or **Branches → Add classic branch protection rule**, for `main`:
- Require a pull request before merging (1 approval)
- Require status checks to pass: `ci / validate`
- Block force pushes

## 5.3 Local tools (macOS)
```bash
brew install gh            # GitHub CLI: lets Copilot open PRs
gh auth login              # GitHub.com → HTTPS → login with browser
pip3 install pyyaml        # used by tools/build_synapse.py
```

## 5.4 Connect this folder to the repo
```bash
cd ~/Desktop/GithubCopilot_coding
git init
git remote add origin https://github.com/<you>/<repo>.git
git fetch origin
git switch -c feat/initial-setup origin/main   # work on a branch, never on main
```
Then commit the scaffold and open the first PR. Copilot can do this with the git-pr-workflow skill.

## 5.5 Copilot settings for the team
- Each developer adds the Foundry model in VS Code (see 02), using **their own key** or a shared team deployment.
- `.github/copilot-instructions.md`, `.github/instructions/`, `.github/prompts/`, `.github/agents/` and `.github/skills/` are picked up automatically when the folder is opened.
