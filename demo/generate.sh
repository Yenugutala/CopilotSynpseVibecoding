#!/usr/bin/env bash
# Demo: ask GitHub Copilot (VS Code, Agent mode) to generate all specs, SQL and the
# Synapse pipeline in one run, and commit them on your CURRENT LOCAL branch.
# Nothing is pushed - push and open the PR to main yourself when you are ready.
#
# Run it from the VS Code terminal of the GithubCopilot_coding window:
#   ./demo/generate.sh             # current branch must not be main
#   ./demo/generate.sh --force     # run even if generated files already exist
#
# Copilot uses the model selected in the chat (e.g. Claude Sonnet 5.5) and asks you to
# click Allow / Keep for commands and file edits.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FORCE=false
[ "${1:-}" = "--force" ] && FORCE=true

if ! command -v code >/dev/null 2>&1; then
    echo "The 'code' command is missing. In VS Code: Cmd+Shift+P -> 'Shell Command: Install code command in PATH'."
    exit 1
fi

# 1. Never work on main
branch="$(git branch --show-current)"
if [ "$branch" = "main" ]; then
    echo "You are on main. Switch to (or create) a local branch first, e.g.:"
    echo "  git switch -c demo/customer-orders"
    exit 1
fi
echo "Working on local branch: $branch"

# 2. Start from a clean slate
existing="$(find specs/sources specs/models sql -name '*.yaml' -o -name '*.sql' 2>/dev/null | grep -v '/_templates/' || true)"
if [ -n "$existing" ] && [ "$FORCE" = false ]; then
    echo "Generated files already exist:"
    echo "$existing" | sed 's/^/  /'
    echo "Run ./demo/revert.sh first, or ./demo/generate.sh --force to keep them."
    exit 1
fi

# 3. Make sure the build tool works before handing over to Copilot
./tools/build.sh validate >/dev/null

# 4. Hand the whole job to Copilot in the current VS Code window
echo "Sending the generate-all prompt to Copilot in VS Code..."
code chat --mode agent --reuse-window \
    --add-file .github/prompts/generate-all.prompt.md \
    "Run every step in the attached generate-all.prompt.md, in order, without stopping for review."

cat <<'EOF'

Copilot is now working in the VS Code Chat panel.
  - Click "Allow" / "Keep" when it asks to run a command or save a file.
  - It finishes by committing on this local branch (no push).
  - When you are ready:  git push -u origin HEAD   and open the PR to main.
EOF
