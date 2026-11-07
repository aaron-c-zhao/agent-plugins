#!/usr/bin/env bash
# Install agenthub on a device: clone the hub, expose the CLI, sync.
#
#   ./install.sh                         # clone the default repo
#   ./install.sh --src ~/src/agent-plugins   # use an existing checkout
#   ./install.sh --repo git@github.com:you/agent-hub.git
#   ./install.sh --no-sync
set -euo pipefail

REPO_URL="${AGENTHUB_REPO_URL:-git@github.com:aaron-c-zhao/agent-plugins.git}"
DEST="${AGENTHUB_HOME:-$HOME/.local/share/agent-plugins}"
BIN_DIR="${AGENTHUB_BIN_DIR:-$HOME/.local/bin}"
SRC=""
DO_SYNC=1

while [ $# -gt 0 ]; do
  case "$1" in
    --src) SRC="$2"; shift 2 ;;
    --repo) REPO_URL="$2"; shift 2 ;;
    --dest) DEST="$2"; shift 2 ;;
    --no-sync) DO_SYNC=0; shift ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

command -v git >/dev/null || { echo "git is required" >&2; exit 1; }
command -v uv >/dev/null || { echo "uv is required: https://docs.astral.sh/uv/" >&2; exit 1; }

if [ -n "$SRC" ]; then
  DEST="$(cd "$SRC" && pwd)"
  echo "using existing checkout: $DEST"
elif [ -d "$DEST/.git" ]; then
  echo "updating $DEST"
  git -C "$DEST" pull --ff-only
else
  echo "cloning $REPO_URL -> $DEST"
  mkdir -p "$(dirname "$DEST")"
  git clone "$REPO_URL" "$DEST"
fi

mkdir -p "$BIN_DIR"
ln -sfn "$DEST/agenthub" "$BIN_DIR/agenthub"
chmod +x "$DEST/agenthub"
echo "linked $BIN_DIR/agenthub"

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *) echo "add $BIN_DIR to PATH to run 'agenthub' from anywhere" ;;
esac

if [ "$DO_SYNC" -eq 1 ]; then
  "$BIN_DIR/agenthub" sync "$@"
fi
