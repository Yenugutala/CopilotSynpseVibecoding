#!/usr/bin/env bash
# Demo: remove everything Copilot generated (specs, SQL, Synapse pipeline) so the
# demo can be run again from scratch. Templates, rules, skills, tools and the
# sample CSVs are kept.
#
#   ./demo/revert.sh           # delete the generated files locally (nothing committed)
#   ./demo/revert.sh --push    # also commit + push on the current branch (never main)
#
# This only changes the repo. Data already loaded in Azure storage (landing/raw/curated)
# and the published Synapse pipeline stay until you Publish the reverted main.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PUSH=false
[ "${1:-}" = "--push" ] && PUSH=true

branch="$(git branch --show-current)"
if [ "$PUSH" = true ] && [ "$branch" = "main" ]; then
    echo "Refusing to commit on main. Create a branch first: git switch -c chore/demo-reset"
    exit 1
fi

echo "Removing Copilot-generated files..."
find specs/sources specs/models -maxdepth 1 -name '*.yaml' -print -delete
find sql/00_setup sql/bronze sql/silver sql/gold -maxdepth 1 -name '*.sql' -print -delete

echo "Rebuilding synapse/ (removes the generated pipeline)..."
./tools/build.sh build
./tools/build.sh check

echo
git status --short

if [ "$PUSH" = true ]; then
    git add -A specs sql synapse
    if git diff --cached --quiet; then
        echo "Nothing to commit - already reverted."
    else
        git commit --quiet -m "chore: remove Copilot-generated specs, SQL and pipeline (demo reset)"
        git push --quiet -u origin HEAD
        echo "Committed and pushed on $branch - ready for your PR to main."
    fi
else
    echo "Done (local only). Use ./demo/revert.sh --push to commit and push on a branch."
fi
