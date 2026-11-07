# agenthub design notes

## Why this shape

The popular skill formats converged on the open [Agent Skills
specification](https://agentskills.io/specification): a directory with
`SKILL.md`, YAML frontmatter, and optional resources. Codex, OpenCode, Hermes,
Claude Code, Gemini CLI, and others all read that format. What differs is the
directory each agent scans and how each agent names MCP servers in its config.

So the durable design is:

1. **Git is the registry.** Versioning, review, rollback, and offline access
   come for free. Any device syncs with `git pull`.
2. **`~/.agents/skills` is the shared materialization point.** It is the
   emerging cross-agent convention. OpenCode reads it globally, Hermes reads it
   through `skills.external_dirs`, and other agents can be symlinked to it.
3. **MCP is rendered, not copied.** One catalog is translated into each
   agent's native format. No per-agent divergence in the source of truth.
4. **The gateway is optional.** A gateway is useful for central credentials and
   auditing, but requiring one would make local stdio servers and offline work
   worse. The catalog can target either direct servers or a gateway URL.

## Sync semantics

- Symlinks are absolute, so moving the shell's cwd never breaks a skill.
- `--copy` exists for Windows or for devices where symlinks are undesirable.
- Existing files are conflicts by default. `--force` moves them to
  `~/.local/state/agenthub/quarantine/<timestamp>/` before linking.
- Config writes are atomic and preceded by a timestamped backup.
- TOML and YAML are edited with round-trip parsers (`tomlkit`, `ruamel.yaml`)
  to preserve comments and unrelated settings. JSONC is parsed with `json5`;
  comments in OpenCode configs are not preserved on write.
- The state file records what agenthub owns, so `--prune` never deletes a
  server or skill the user added by hand.

## Adding an agent

Add a `Target` in `default_targets()`:

```python
"myagent": Target(
    name="myagent",
    binary="myagent",
    base=home / ".myagent",
    skills_dir=home / ".myagent" / "skills",
    mcp_config=home / ".myagent" / "config.json",
    mcp_format="claude-json",
),
```

Then add a renderer if the config shape differs, and an entry in
`_render_for()`. Keep the adapter data-only where possible.

## Adding an asset type

Use `assets:` in `hub.yaml`; no code change is needed for directory-shaped
assets:

```yaml
assets:
  rules:
    source: rules
    install:
      codex: ~/.codex/rules
      claude: ~/.claude/rules
  commands:
    source: commands
    install:
      opencode: ~/.config/opencode/commands
```

Every entry in the source directory is symlinked into each target directory.
`--prune` removes links agenthub previously created.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Skill not visible | `agenthub status`; does the agent read `~/.agents/skills`? For Hermes, confirm `skills.external_dirs` in `~/.hermes/config.yaml`. |
| MCP shows auth errors | The agent may be attempting OAuth. Set `oauth: false` for header/API-key servers. |
| Codex warns about a mixed value | Codex cannot interpolate `${VAR}` inside a larger string. Use an exact `${VAR}` or a literal. |
| OpenCode ignores a server | Run `opencode mcp list`. V2 stores servers under `mcp.servers`; V1 stores them under `mcp`. agenthub detects and preserves the existing shape. |
| `update` refuses to pull | Commit or stash local changes, or pass `--force` to pull over a dirty tree. |
| Config parse error | The original is in `~/.local/state/agenthub/backups/`; fix the file, then re-run `agenthub sync`. |

## Prior art considered

- **Git + symlinks** (this design): simplest, agent-agnostic, no runtime.
- **GitHub CLI `gh skill`**: excellent for installing third-party skills with
  pinning, but does not manage MCP or per-device MCP config.
- **Grimoire / grim**: OCI-based package manager for skills, rules, agents, and
  MCP; promising but young and not needed for a single-user fleet.
- **Skills Manager (desktop)**: broad agent support including Hermes, but GUI
  first and skills-only.
- **Docker MCP Gateway / MetaMCP / IBM ContextForge**: strong MCP gateways;
  used here as an optional endpoint rather than a required control plane.
