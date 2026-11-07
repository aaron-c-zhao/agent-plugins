#!/usr/bin/env bash
# Offline smoke test: exercises sync, idempotence, and shape preservation
# against a throwaway HOME. Run from the repo root: tests/smoke.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT

mkdir -p "$T/.codex" "$T/.config/opencode" "$T/.hermes"
cat > "$T/.codex/config.toml" <<'EOF'
# codex fixture
model = "test"

[mcp_servers.existing]
command = "echo"
EOF
cat > "$T/.config/opencode/opencode.jsonc" <<'EOF'
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "existing": {"type": "local", "command": ["echo"], "enabled": true}
  }
}
EOF
cat > "$T/.hermes/config.yaml" <<'EOF'
model:
  default: test/model
mcp_servers:
  existing:
    command: echo
skills:
  create_dir: ~/.hermes/skills
EOF

run() { HOME="$T" "$ROOT/agenthub" "$@"; }

run sync --target agents,codex,opencode,hermes >/dev/null

# Skills are linked, not copied, and the original configs survive.
test -L "$T/.agents/skills/openspec-explore"
test -L "$T/.codex/skills/openspec-explore"
grep -q 'model = "test"' "$T/.codex/config.toml"
grep -q 'existing' "$T/.config/opencode/opencode.jsonc"
grep -q 'create_dir' "$T/.hermes/config.yaml"

# Every target received the catalog entry.
grep -q '\[mcp_servers.homeassistant\]' "$T/.codex/config.toml"
grep -q '"homeassistant"' "$T/.config/opencode/opencode.jsonc"
grep -q 'homeassistant:' "$T/.hermes/config.yaml"

# Hermes is pointed at the shared skill directory.
grep -q '~/.agents/skills' "$T/.hermes/config.yaml"

# Idempotent.
before="$(sha256sum "$T/.codex/config.toml" "$T/.config/opencode/opencode.jsonc" "$T/.hermes/config.yaml")"
run sync --target agents,codex,opencode,hermes >/dev/null
after="$(sha256sum "$T/.codex/config.toml" "$T/.config/opencode/opencode.jsonc" "$T/.hermes/config.yaml")"
test "$before" = "$after"

# A brand-new OpenCode install gets the V2 shape (mcp.servers).
N="$T/new"; mkdir -p "$N"
HOME="$N" "$ROOT/agenthub" sync --target agents,opencode >/dev/null
grep -q '"servers"' "$N/.config/opencode/opencode.jsonc"

# Status exits cleanly.
run status >/dev/null

echo "smoke test passed"
