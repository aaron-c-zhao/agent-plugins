# agent-plugins

One Git repository for the skills, MCP servers, rules, prompts, and other
assets used by AI agents across all my devices.

The repo is the source of truth. A small CLI (`agenthub`) materializes it into
the native locations each agent reads. No server, no database, no copy drift:
skills are symlinked, MCP entries are rendered into each agent's own config.

## What it manages

| Asset | Canonical location | How it reaches agents |
| --- | --- | --- |
| Skills | `.agents/skills/*/SKILL.md` | `~/.agents/skills` (the cross-agent convention), plus symlinks for Codex/Claude/Gemini |
| MCP servers | `mcp/servers.yaml` | Rendered into Codex `config.toml`, OpenCode `opencode.jsonc`, Hermes `config.yaml`, Claude `.claude.json` |
| Rules, prompts, commands | `rules/`, `prompts/`, `commands/` | Optional `assets:` mapping in `hub.yaml` |
| Per-device overrides | `mcp/servers.local.yaml` (gitignored) | Deep-merged over the shared MCP catalog |

Hermes and OpenCode read `~/.agents/skills` natively (Hermes via
`skills.external_dirs`), so one linked directory serves several agents.

## Install on a device

```bash
# Fresh device: clone, link the CLI, detect agents, sync
./install.sh

# Or point at an existing checkout
./install.sh --src ~/workspace/agent-plugins

# Add ~/.local/bin to PATH if the installer says so
export PATH="$HOME/.local/bin:$PATH"
```

Requirements: `git` and [`uv`](https://docs.astral.sh/uv/). The first run
downloads the CLI's three Python dependencies into uv's cache; nothing is
installed globally.

## Daily use

```bash
agenthub tui                 # interactive dashboard
agenthub status              # what is out of sync on this device
agenthub update              # git pull --ff-only, then sync
agenthub sync                # re-materialize without pulling
agenthub sync --dry-run      # show the plan
agenthub sync --prune        # remove links/entries deleted from the repo
agenthub mcp list            # inspect the catalog
agenthub doctor              # paths, parse errors, missing env vars
```

`sync` is idempotent and backs up every config file it changes under
`~/.local/state/agenthub/backups/`. Untracked servers and skills are left
alone; `--prune` only removes things agenthub previously managed.

## Add a skill

```bash
mkdir -p .agents/skills/my-skill
$EDITOR .agents/skills/my-skill/SKILL.md
agenthub sync
git add .agents/skills/my-skill && git commit -m "Add my-skill"
git push
```

On another device: `agenthub update`.

## Add or change an MCP server

Edit `mcp/servers.yaml`:

```yaml
servers:
  context7:
    transport: http
    url: https://mcp.context7.com/mcp
    headers:
      CONTEXT7_API_KEY: ${CONTEXT7_API_KEY}
    oauth: false
```

Never commit secrets. Use `${VAR}` placeholders. Each agent resolves them from
its environment; Hermes additionally reads `~/.hermes/.env`.

Device-specific differences (hostnames, absolute paths, extra servers) go in
`mcp/servers.local.yaml` — copy `mcp/servers.local.yaml.example` to start. That
file is gitignored.

```yaml
servers:
  homeassistant:
    env:
      HASS_HOST: http://192.168.1.20:8123
```

## Optional: one gateway endpoint

The catalog works without any extra infrastructure. If you later want central
credentials, auditing, or a single HTTP endpoint for remote devices, run an
open-source MCP gateway (for example Docker MCP Gateway or MetaMCP) and point
the catalog at it on that device:

```yaml
# mcp/servers.local.yaml
servers:
  gateway:
    transport: http
    url: http://gateway.local:8080/mcp
    targets: [codex, opencode, hermes]
```

Disable the direct servers in the same file if the gateway already exposes
them. This keeps the gateway optional rather than a hard dependency.

## Supported targets

| Target | Skills | MCP |
| --- | --- | --- |
| `codex` | `~/.codex/skills` symlinks | `~/.codex/config.toml` (`mcp_servers`) |
| `opencode` | `~/.agents/skills` | `~/.config/opencode/opencode.jsonc` (V1 or V2 shape, auto-detected) |
| `hermes` | `~/.agents/skills` via `skills.external_dirs` | `~/.hermes/config.yaml` (`mcp_servers`) |
| `claude` | `~/.claude/skills` symlinks | `~/.claude.json` (`mcpServers`) |
| `gemini` | `~/.gemini/skills` symlinks | not yet |
| `agents` | `~/.agents/skills` symlinks (shared) | — |

Add another agent by editing the target table in `agenthub` and, if needed,
overriding paths in `hub.yaml`. The adapters are intentionally small.

## Layout

```
agent-plugins/
├── agenthub                 # CLI entry point (uv PEP 723 script)
├── agenthub_core.py         # shared discovery/sync/config logic
├── agenthub_tui.py          # Textual terminal UI
├── hub.yaml                 # targets, skill source, optional assets
├── mcp/
│   ├── servers.yaml         # shared MCP catalog
│   ├── servers.local.yaml   # per-device overrides (gitignored)
│   └── servers.local.yaml.example
├── .agents/skills/          # canonical Agent Skills
├── install.sh
├── tests/smoke.sh           # offline sync test
└── docs/agenthub.md         # design notes and troubleshooting
```

## Guidelines

- Keep each skill self-contained with its own `SKILL.md` and README.
- Never commit secrets (API keys, tokens); use `${VAR}` or `.env` (gitignored).
- Prefer the open Agent Skills format (`SKILL.md`) so assets stay portable.
- Run `agenthub doctor` after changing paths or adding a new device.

## License

TBD
