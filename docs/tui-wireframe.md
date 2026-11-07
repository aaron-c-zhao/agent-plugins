# agenthub TUI — wireframe (v1 draft)

Status: design draft for review. No implementation yet.

Ideal terminal: **110×36**. Minimum: **80×24** (columns collapse).

## Conventions

| Glyph | Meaning |
|---|---|
| `✓` | in sync / installed |
| `●` | missing |
| `~` | drift (config differs) |
| `!` | conflict or warning |
| `-` | not applicable / disabled |
| `ext` | provided via `~/.agents/skills` external dir |

## 1. Dashboard

```
┌ agenthub ──────────────────────────────────────────────────────────────────────────────────────┐
│ agent-plugins   main ↑3   clean     targets 4/6    skills 6    mcp 1/2        synced 2m ago   │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Dashboard │ Skills │ MCP │ Targets │ Doctor                                                      │
├─────────────────────────────────────────────────────┬───────────────────────────────────────────┤
│ Attention                                           │ Targets                                   │
│  ! 1 commit behind origin/main                      │  ✓ agents    ~/.agents/skills     6/6  -  │
│  ! HA_TOKEN not set in this shell                   │  ✓ codex     ~/.codex             6/6 1/1 │
│  ● 2 skills missing in codex                        │  ✓ opencode  ~/.config/opencode   6/6 1/1 │
│  ~ 1 MCP config drift in opencode                   │  - hermes    not detected                 │
│  ! 1 unmanaged conflict                             │  - claude    not detected                 │
│                                                     │  ✓ gemini    ~/.gemini            6/6  -  │
│                                                     │                                           │
│ Quick actions                                       │ Repository                                │
│  [S] Sync all                                       │  branch   main                            │
│  [U] Update from origin                             │  remote   1 behind, 0 ahead               │
│  [D] Doctor                                         │  state    ~/.local/state/agenthub         │
│  [P] Preview prune                                  │  backup   2026-11-07 17:38                │
├─────────────────────────────────────────────────────┴───────────────────────────────────────────┤
│ s sync   u update   p prune   r refresh   / filter   ? help   q quit                            │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## 2. Skills

```
┌ agenthub ──────────────────────────────────────────────────────────────────────────────────────┐
│ agent-plugins   main   clean    6 skills · 0 conflicts · 0 orphans                              │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Dashboard │ Skills │ MCP │ Targets │ Doctor                                                      │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Filter: _                                           agents  codex  opencode  hermes  claude      │
│ ┌──────────────────────────────┬────────────┬───────┬───────┬────────┬────────┬────────┐         │
│ │ Skill                        │ Category   │ agents│ codex │ opencode│ hermes │ claude │         │
│ ├──────────────────────────────┼────────────┼───────┼───────┼────────┼────────┼────────┤         │
│ │ openspec-explore             │ —          │  ✓    │  ✓    │   ✓    │  ext   │   ✓    │         │
│ │ openspec-propose             │ —          │  ✓    │  ✓    │   ✓    │  ext   │   ✓    │         │
│ │ openspec-apply-change        │ —          │  ✓    │  ✓    │   ✓    │  ext   │   ✓    │         │
│ │ my-skill                     │ devops     │  ●    │  ●    │   ✓    │  ext   │   ●    │         │
│ └──────────────────────────────┴────────────┴───────┴───────┴────────┴────────┴────────┘         │
│ ┌ my-skill ───────────────────────────────────────────────────────────────────────┐              │
│ │ Description: Deploy services to the staging environment.                        │              │
│ │ Source:      .agents/skills/devops/my-skill/SKILL.md                             │              │
│ │ Issue:       2 missing links (agents, codex)                                     │              │
│ └─────────────────────────────────────────────────────────────────────────────────┘              │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ space sync selected   e edit SKILL.md   o open folder   p prune orphans   / filter   esc back   │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Notes:

- OpenCode/Hermes show `ext` because they read `~/.agents/skills`.
- `e` suspends the TUI and opens `$EDITOR`.
- Per-agent skill exclusion is **not** in v1; it is a repo-level concept.

## 3. MCP servers

```
┌ agenthub ──────────────────────────────────────────────────────────────────────────────────────┐
│ agent-plugins   main   clean    2 servers · 1 enabled · 1 device override                       │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Dashboard │ Skills │ MCP │ Targets │ Doctor                                                      │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Filter: _                                                                                        │
│ ┌────────────────────┬─────────┬────────┬───────────────┬────────┬──────────┬────────┐          │
│ │ Server             │ Type    │ State  │ Scope         │ codex  │ opencode │ hermes │          │
│ ├────────────────────┼─────────┼────────┼───────────────┼────────┼──────────┼────────┤          │
│ │ homeassistant      │ stdio   │ on     │ device        │  ✓     │    ✓     │  ext   │          │
│ │ context7           │ http    │ off    │ shared        │  -     │    -     │  -     │          │
│ └────────────────────┴─────────┴────────┴───────────────┴────────┴──────────┴────────┘          │
│ ┌ homeassistant ──────────────────────────────────────────────────────────────────┐               │
│ │ command: /home/me/.local/bin/uvx homeassistant-mcp                               │               │
│ │ env:     HASS_HOST=set    HASS_TOKEN=${HA_TOKEN} ✓                               │               │
│ │ targets: codex, opencode, hermes, claude                                         │               │
│ └──────────────────────────────────────────────────────────────────────────────────┘               │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ space toggle (this device)   E edit shared catalog   l edit local override   s sync   o config  │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Safety decision: `space` writes to `mcp/servers.local.yaml` only. Shared
toggles require `E`, which opens the catalog in `$EDITOR`.

## 4. Targets

```
┌ agenthub ──────────────────────────────────────────────────────────────────────────────────────┐
│ agent-plugins   main   clean    targets 4/6                                                   │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Dashboard │ Skills │ MCP │ Targets │ Doctor                                                      │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ ┌──────────┬──────────┬────────────────────────────┬──────────────────────────┬───────┬───────┐ │
│ │ Target   │ Detected │ Skills dir                 │ MCP config               │ Skill │ MCP   │ │
│ ├──────────┼──────────┼────────────────────────────┼──────────────────────────┼───────┼───────┤ │
│ │ agents   │ yes      │ ~/.agents/skills           │ —                        │ 6/6   │  —    │ │
│ │ codex    │ yes      │ ~/.codex/skills            │ ~/.codex/config.toml     │ 6/6   │ 1/1   │ │
│ │ opencode │ yes      │ external                   │ ~/.config/opencode/...   │ 6/6   │ 1/1   │ │
│ │ hermes   │ no       │ ~/.hermes/skills           │ ~/.hermes/config.yaml    │  —    │  —    │ │
│ │ claude   │ no       │ ~/.claude/skills           │ ~/.claude.json           │  —    │  —    │ │
│ │ gemini   │ yes      │ ~/.gemini/skills           │ —                        │ 6/6   │  —    │ │
│ └──────────┴──────────┴────────────────────────────┴──────────────────────────┴───────┴───────┘ │
│ ┌ codex ─────────────────────────────────────────────────────────────────────────┐              │
│ │ Status: in sync          Last sync: 2m ago        Backup: 17:38                 │              │
│ │ Skills: 6 linked, 0 missing, 0 conflicts                                        │              │
│ │ MCP:    1 managed, 0 drift, 0 orphan                                            │              │
│ └─────────────────────────────────────────────────────────────────────────────────┘              │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ s sync target   o open config   b backups   esc back                                            │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## 5. Doctor

```
┌ agenthub ──────────────────────────────────────────────────────────────────────────────────────┐
│ agent-plugins   main   clean                                                                   │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Dashboard │ Skills │ MCP │ Targets │ Doctor                                                      │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Environment                                                                                    │
│   ✓ git 2.51           ✓ uv 0.8             ✓ python 3.15                                      │
│ Repository                                                                                     │
│   ✓ hub.yaml valid      ✓ 6 skills found     ✓ 2 MCP servers                                   │
│ Targets                                                                                        │
│   ✓ codex config parses   ✓ opencode config parses   - hermes not installed                    │
│ Secrets                                                                                        │
│   ✓ HA_TOKEN set          ! CONTEXT7_API_KEY not set (server disabled)                         │
│ Git                                                                                            │
│   ! 1 commit behind origin/main                                                                 │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ r rerun   c copy report   esc back                                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## 6. Sync preview (modal)

```
┌ Sync preview ──────────────────────────────────────────────────────────────────────────────────┐
│ Plan                                                                                           │
│   Skills   agents +2    codex +2    opencode ext    gemini +2                                  │
│   MCP      codex ~1     opencode ~1    hermes skipped (not detected)                           │
│   Conflicts 1: ~/.codex/skills/my-skill exists and is not managed                              │
│                                                                                                │
│ Diff                                                                                           │
│   --- a/~/.codex/config.toml                                                                   │
│   +++ b/~/.codex/config.toml                                                                   │
│   @@ -12,6 +12,10 @@                                                                            │
│    [mcp_servers.homeassistant]                                                                 │
│   -command = "uvx"                                                                             │
│   +command = "/home/me/.local/bin/uvx"                                                         │
│   +[mcp_servers.homeassistant.env]                                                             │
│   +HASS_HOST = "http://homeassistant.local:8123"                                               │
│                                                                                                │
│ Backups: ~/.local/state/agenthub/backups/20261107-180000                                       │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ [a] Apply all   [c] Apply and skip conflicts   [esc] Cancel                                    │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## 7. Update confirmation

```
┌ Update from origin ──────────────────────────────────────┐
│ Branch main is 1 commit behind origin/main.              │
│                                                          │
│  3 files changed                                         │
│   .agents/skills/pdf-tools/SKILL.md                      │
│   mcp/servers.yaml                                       │
│   AGENTS.md                                              │
│                                                          │
│ Pull with --ff-only, then open the sync preview?         │
│                                                          │
│ [p] Pull & preview    [esc] Cancel                       │
└──────────────────────────────────────────────────────────┘
```

## 8. Empty / first-run state

```
┌ agenthub ────────────────────────────────────────────────┐
│                                                          │
│  No agent targets detected.                              │
│                                                          │
│  Install an agent, or force a target:                    │
│                                                          │
│    agenthub sync --target codex,opencode                 │
│                                                          │
│  [?] Help      [q] Quit                                  │
└──────────────────────────────────────────────────────────┘
```

## Interaction model

| Key | Action |
|---|---|
| `1`–`5` / `Tab` | Switch tab |
| `↑` `↓` `j` `k` | Move selection |
| `Enter` | Open detail |
| `/` | Filter current list |
| `s` | Sync (opens preview) |
| `u` | Update from origin |
| `p` | Prune preview |
| `r` | Refresh |
| `e` | Edit canonical file in `$EDITOR` |
| `o` | Open config/folder |
| `?` | Help overlay |
| `q` | Quit |

All mutations go through a preview modal. No silent writes.

## MVP scope

In v1:

- Dashboard, Skills, MCP, Targets, Doctor.
- Detect and display drift.
- `sync`, `update`, `prune` with preview/diff.
- Enable/disable MCP **for this device** via `servers.local.yaml`.
- Open canonical files in `$EDITOR`.
- Backups, conflicts, quarantine reporting.

Deferred:

- Inline form editors for `SKILL.md` / `servers.yaml`.
- Installing a skill directly from a Git URL inside the TUI.
- Per-agent skill inclusion/exclusion.
- Gateway management UI.
- Push/commit actions from the TUI.

## Technical note

Use **Textual** (Python, same runtime as agenthub, works over SSH). Refactor
the current script into:

```
agenthub_core.py   # discovery, rendering, sync, status
agenthub          # CLI wrapper
agenthub_tui.py   # Textual app
```

The TUI should import the core directly rather than shelling out to the CLI,
so previews and writes use exactly the same logic.
