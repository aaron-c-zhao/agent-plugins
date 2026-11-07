# AGENTS.md

This repo is the canonical source of truth for skills and MCP servers used by
Codex, OpenCode, Hermes, Claude, and Gemini. `agenthub` links `.agents/skills`
into `~/.agents/skills` and renders `mcp/servers.yaml` into each agent's native
config.

## Rules

- Edit canonical files only: `.agents/skills/` and `mcp/servers.yaml`.
- Device-specific changes go in `mcp/servers.local.yaml` (gitignored).
- Never hand-edit managed entries in `~/.codex/config.toml`,
  `~/.config/opencode/opencode.jsonc`, `~/.hermes/config.yaml`, or
  `~/.claude.json`.
- Never commit secrets. Use `${VAR}` placeholders.
- Never delete or change an entry `agenthub` does not manage.
- Run `agenthub sync --dry-run` before using `--prune` or `--force`.
- Do not install permanent skills with `gh skill install` or
  `hermes skills install`. Vendor them into `.agents/skills/` instead.
- Commit verified changes. Never push without explicit confirmation.

## Commands

```bash
agenthub tui                     # interactive dashboard
agenthub status                  # drift per target
agenthub doctor                  # paths, parse errors, missing env vars
agenthub sync                    # apply skills + MCP config
agenthub sync --dry-run          # preview
agenthub sync --prune --dry-run  # preview removals
agenthub update                  # git pull --ff-only, then sync
agenthub mcp list                # inspect the MCP catalog
```

## Add a skill

```bash
mkdir -p .agents/skills/<name>
$EDITOR .agents/skills/<name>/SKILL.md   # frontmatter: name, description
agenthub sync
agenthub status
git add .agents/skills/<name>
git commit -m "Add <name> skill"
```

The directory must contain `SKILL.md`. The `description` must state when the
skill should be used.

## Add or change an MCP server

Edit `mcp/servers.yaml`:

- stdio: set `command` (and optional `args`, `env`).
- http: set `url` (and optional `headers`).
- Use `${VAR}` for secrets.
- Use `targets` to limit which agents receive it.

Then run:

```bash
agenthub sync
agenthub status
```

For this device only, create `mcp/servers.local.yaml` (see the `.example` file)
and run `agenthub sync` again. Do not commit it.

## Verify before reporting done

```bash
agenthub doctor
agenthub status
tests/smoke.sh
git diff --check
```

Confirm `git diff` contains no secrets and the change is committed.

## Ask the human first

- Pushing to the remote.
- Deleting an existing skill or MCP server.
- Changing target paths or adding a new agent adapter.
- Using `--force` on a device you did not configure.
- Adding real credentials or a gateway endpoint.
