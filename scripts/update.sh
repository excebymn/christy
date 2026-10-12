#!/usr/bin/env bash
# Recovery path for updating when the `christy` binary itself is missing or
# broken. Normally just run `christy update`: it does the same and also
# reports which tools were added, changed, or removed.
#
# Pulls the latest changes and always rebuilds the core.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

command -v git >/dev/null 2>&1 || { echo "error: git not found" >&2; exit 1; }
command -v cargo >/dev/null 2>&1 || { echo "error: cargo not found" >&2; exit 1; }

echo "==> pulling the latest changes"
git -C "$REPO" pull --ff-only

echo "==> rebuilding the core"
cargo build --release --manifest-path "$REPO/core/Cargo.toml"

echo "done. Run \`christy doctor\` to check everything."
