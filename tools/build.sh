#!/usr/bin/env bash
# Run tools/build_synapse.py inside the project's own Python environment.
# Creates .venv and installs requirements.txt on first use, so nobody has to
# remember an interpreter path or install packages by hand.
#
# Usage: ./tools/build.sh validate | build | check
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT/.venv"
PY="$VENV/bin/python3"

if [ ! -x "$PY" ]; then
    echo "Creating project environment in .venv (first run only)..."
    python3 -m venv "$VENV"
fi

if ! "$PY" -c "import yaml" >/dev/null 2>&1; then
    echo "Installing requirements.txt into .venv (first run only)..."
    "$PY" -m pip install --quiet --disable-pip-version-check -r "$ROOT/requirements.txt"
fi

exec "$PY" "$ROOT/tools/build_synapse.py" "$@"
