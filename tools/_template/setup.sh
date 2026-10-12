#!/usr/bin/env bash
# Prepares everything this tool needs. christy runs it (with the terminal
# attached, so sudo and confirmations work) when something is missing.
#
# Rules:
#   - Be idempotent: running it twice must be safe.
#   - Exit non-zero on failure.
#   - Use CHRISTY_TOOL_DIR / CHRISTY_STATE_DIR instead of guessing paths.
set -euo pipefail

echo "nothing to install for mytool"

# Example: install a system package on Arch (sudo will prompt for a password)
#   command -v ffmpeg >/dev/null || sudo pacman -S --needed ffmpeg
#
# Example: python tool with its own venv
#   VENV="$CHRISTY_STATE_DIR/envs/mytool"
#   python3 -m venv "$VENV"
#   "$VENV/bin/python" -m pip install -q -r "$CHRISTY_TOOL_DIR/requirements.txt"
