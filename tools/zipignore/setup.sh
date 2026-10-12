#!/usr/bin/env bash
# Builds the isolated venv for zipignore and installs its requirements.
# The core passes CHRISTY_TOOL_DIR and CHRISTY_STATE_DIR; the fallbacks below
# keep this script usable when run by hand.
set -euo pipefail

TOOL_DIR="${CHRISTY_TOOL_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
STATE_DIR="${CHRISTY_STATE_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/christy}"
VENV_DIR="$STATE_DIR/envs/zipignore"

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found. install it first:" >&2
    echo "  sudo pacman -S python        (arch)" >&2
    echo "  sudo apt install python3     (debian/ubuntu)" >&2
    exit 1
fi

echo "creating venv at $VENV_DIR"
if ! python3 -m venv "$VENV_DIR"; then
    echo "couldn't create the venv. on debian/ubuntu you may need: sudo apt install python3-venv" >&2
    exit 1
fi

echo "installing requirements"
"$VENV_DIR/bin/python" -m pip install -q -r "$TOOL_DIR/requirements.txt"

echo "zipignore is ready"
