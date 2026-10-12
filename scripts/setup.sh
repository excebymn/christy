#!/usr/bin/env bash
# One-time bootstrap for christy:
#   1. builds the Rust core
#   2. links the binary into ~/.local/bin
#   3. writes ~/.config/christy/config.toml so christy can always find this repo
#   4. runs `christy doctor`
#
# Tool dependencies are NOT installed here. Each tool offers its own setup the
# first time it is run. Safe to run again.
#
# Overrides (all optional):
#   CHRISTY_BIN_DIR      where to link the binary   (default: ~/.local/bin)
#   CHRISTY_CONFIG_DIR   where config.toml goes     (default: ~/.config/christy)
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="${CHRISTY_BIN_DIR:-$HOME/.local/bin}"
CONFIG_DIR="${CHRISTY_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/christy}"
BINARY="$REPO/core/target/release/christy"

say() { printf '==> %s\n' "$1"; }
die() { printf 'error: %s\n' "$1" >&2; exit 1; }

command -v cargo >/dev/null 2>&1 || die "cargo not found. Install Rust first:
  sudo pacman -S rust        (arch)
  https://rustup.rs          (anything else)"

# config.toml stores the path as a TOML literal string, which can't hold a quote
case "$REPO" in
    *"'"*) die "the repo path contains a single quote, which config.toml can't store: $REPO" ;;
esac

say "building the core (cargo build --release)"
cargo build --release --manifest-path "$REPO/core/Cargo.toml"

say "linking $BIN_DIR/christy"
mkdir -p "$BIN_DIR"
ln -sf "$BINARY" "$BIN_DIR/christy"

say "writing $CONFIG_DIR/config.toml"
mkdir -p "$CONFIG_DIR"
printf "repo_path = '%s'\n" "$REPO" > "$CONFIG_DIR/config.toml"

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
        printf '\nnote: %s is not in your PATH. Add this to your shell config:\n' "$BIN_DIR"
        printf '  export PATH="%s:$PATH"\n\n' "$BIN_DIR"
        ;;
esac

say "checking everything with christy doctor"
"$BIN_DIR/christy" doctor || true

printf '\nAll set. Try: christy list\n'
