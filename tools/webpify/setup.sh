#!/usr/bin/env bash
# Builds the isolated venv for webpify and installs its requirements.
# The core passes CHRISTY_TOOL_DIR and CHRISTY_STATE_DIR; the fallbacks below
# keep this script usable when run by hand.
set -euo pipefail

TOOL_DIR="${CHRISTY_TOOL_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
STATE_DIR="${CHRISTY_STATE_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/christy}"
VENV_DIR="$STATE_DIR/envs/webpify"

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

# Pillow's wheels bundle WebP support; say so early if this build doesn't have it.
if ! "$VENV_DIR/bin/python" -c 'from PIL import features; raise SystemExit(0 if features.check("webp") else 1)'; then
    echo "this Pillow build has no WebP support. try: $VENV_DIR/bin/python -m pip install --force-reinstall --only-binary :all: Pillow" >&2
    exit 1
fi

echo "webpify is ready"
