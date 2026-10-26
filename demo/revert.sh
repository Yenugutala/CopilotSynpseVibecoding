#!/usr/bin/env bash
# Demo: remove everything Copilot generated (specs, SQL, Synapse pipeline) so the
# demo can be run again from scratch. Templates, rules, skills, tools and the
# sample CSVs are kept.
#
#   ./demo/revert.sh            # delete the generated files (nothing committed)
#   ./demo/revert.sh --commit   # also commit the removal on the current local branch (never main, no push)
#
# This only changes the repo. Data already loaded in Azure storage (landing/raw/curated)
# and the published Synapse pipeline stay until you Publish the reverted main.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COMMIT=false
[ "${1:-}" = "--commit" ] && COMMIT=true

branch="$(git branch --show-current)"
if [ "$COMMIT" = true ] && [ "$branch" = "main" ]; then
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

if [ "$COMMIT" = true ]; then
    git add -A specs sql synapse
    if git diff --cached --quiet; then
        echo "Nothing to commit - already reverted."
    else
        git commit --quiet -m "chore: remove Copilot-generated specs, SQL and pipeline (demo reset)"
        echo "Committed on local branch $branch (not pushed)."
    fi
else
    echo "Done (files deleted, nothing committed). Use ./demo/revert.sh --commit to commit on this branch."
fi
