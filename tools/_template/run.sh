#!/usr/bin/env bash
# Entry point. christy runs this in the directory the user called it from and
# passes every argument through untouched.
#
# Available environment variables:
#   CHRISTY_HOME        the repo root
#   CHRISTY_TOOL_DIR    this tool's folder
#   CHRISTY_STATE_DIR   where christy keeps state and per-tool environments
#   CHRISTY_VERSION     the christy version
set -euo pipefail

usage() {
    cat <<USAGE
usage: mytool [-h] [name]

say hello (replace this with your tool)
USAGE
}

# Every tool must answer --help (christy help <tool> relies on it).
case "${1:-}" in
    -h | --help)
        usage
        exit 0
        ;;
esac

echo "hello, ${1:-world}"
