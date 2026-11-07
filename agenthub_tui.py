#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "tomlkit>=0.13",
#   "ruamel.yaml>=0.18",
#   "json5>=0.9",
#   "textual>=0.80",
# ]
# ///
"""Textual TUI for agenthub.

Run with `agenthub tui` (installs Textual through uv on first use) or directly
as `uv run agenthub_tui.py`.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.markup import escape
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Label,
    Static,
    TabbedContent,
    TabPane,
)

import agenthub_core as core

ANSI = re.compile(r"\x1b\[[0-9;]*m")

HELP_TEXT = """\
[bold]agenthub TUI[/bold]

  1..5 / Tab   switch screen
  j/k, arrows  move selection
  Enter        open selected detail
  /            filter (not yet implemented)
  s            preview sync
  u            update from origin, then sync
  r            refresh
  e            edit canonical file in $EDITOR
  space        toggle selected MCP for this device
  ?            this help
  q            quit

All writes go through the same core as the CLI. Config files are backed up
under ~/.local/state/agenthub/backups/ before they are changed.
"""


def clean(text: str) -> str:
    return ANSI.sub("", text)


def capture(fn: Any, *args: Any, **kwargs: Any) -> tuple[int, str]:
    """Call a core function and capture its terminal output."""
    buffer = io.StringIO()
    code = 0
    try:
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            result = fn(*args, **kwargs)
            code = int(result or 0)
    except SystemExit as exc:
        code = int(exc.code or 0)
    except Exception as exc:  # noqa: BLE001 - surface errors in the TUI
        code = 1
        buffer.write(f"{type(exc).__name__}: {exc}\n")
    return code, clean(buffer.getvalue())


def git(*args: str) -> str:
    result = core.run_git(*args)
    return result.stdout.strip() if result.returncode == 0 else ""


@dataclass
class SkillItem:
    rel: str
    name: str
    category: str
    description: str
    path: Path
    status: dict[str, str] = field(default_factory=dict)


@dataclass
class McpItem:
    name: str
    entry: dict[str, Any]
    scope: str
    status: dict[str, str] = field(default_factory=dict)


@dataclass
class UiState:
    targets: list[Any]
    skills: list[SkillItem]
    servers: list[McpItem]
    repo: dict[str, str]
    warnings: list[str]
    state: dict[str, Any]


def read_skill_meta(path: Path) -> tuple[str, str]:
    try:
        text = (path / "SKILL.md").read_text(encoding="utf-8")
    except OSError:
        return path.name, ""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                data = core.YAML(typ="safe").load(parts[1]) or {}
            except Exception:  # noqa: BLE001
                data = {}
            return str(data.get("name") or path.name), str(data.get("description") or "")
    return path.name, ""


def skill_status(target: Any, rel: str, source: Path, state: dict[str, Any]) -> str:
    if target.skills_mode == "external":
        return "ext"
    if target.skills_dir is None or target.skills_mode == "none":
        return "-"
    dest = target.skills_dir / rel
    if dest.is_symlink():
        try:
            return "✓" if dest.resolve() == source.resolve() else "~"
        except OSError:
            return "!"
    if dest.exists():
        return "✓" if rel in state.get("links", {}).get(target.name, {}) else "!"
    return "●"


def mcp_status(target: Any, name: str, entry: dict[str, Any], existing: dict[str, Any]) -> str:
    if not entry.get("enabled", True):
        return "-"
    allowed = entry.get("targets")
    if allowed and target.name not in allowed:
        return "-"
    if target.mcp_format is None:
        return "-"
    desired = core._render_for(target, entry)
    current = existing.get(name)
    if current is None:
        return "●"
    return "✓" if current == desired else "~"


def collect() -> UiState:
    hub = core.load_hub()
    assets = core.load_assets(hub)
    targets = core.build_targets(hub, None)
    servers = core.load_mcp_catalog()
    skills = core.discover_skills(assets)
    state = core.load_state()

    existing: dict[str, dict[str, Any]] = {}
    with contextlib.redirect_stdout(io.StringIO()):
        for target in targets:
            existing[target.name] = core.read_native_servers(target)

    skill_items: list[SkillItem] = []
    for rel, path in skills.items():
        name, description = read_skill_meta(path)
        parts = rel.split("/")
        category = "/".join(parts[:-1]) or "—"
        item = SkillItem(
            rel=rel,
            name=name,
            category=category,
            description=description,
            path=path,
        )
        item.status = {
            target.name: skill_status(target, rel, path, state) for target in targets
        }
        skill_items.append(item)

    mcp_items: list[McpItem] = []
    local_names = core.local_mcp_names()
    for name, entry in sorted(servers.items()):
        item = McpItem(
            name=name,
            entry=dict(entry),
            scope="device" if name in local_names else "shared",
        )
        item.status = {
            target.name: mcp_status(target, name, entry, existing.get(target.name, {}))
            for target in targets
        }
        mcp_items.append(item)

    branch = git("rev-parse", "--abbrev-ref", "HEAD") or "?"
    head = git("log", "-1", "--format=%h %s")
    ahead = behind = 0
    counts = git("rev-list", "--left-right", "--count", "HEAD...@{upstream}")
    if counts:
        try:
            ahead, behind = (int(part) for part in counts.split())
        except ValueError:
            pass
    dirty = bool(git("status", "--porcelain", "--untracked-files=no").strip())
    repo = {
        "branch": branch,
        "head": head,
        "ahead": str(ahead),
        "behind": str(behind),
        "dirty": "yes" if dirty else "no",
    }

    warnings: list[str] = []
    if ahead:
        warnings.append(f"{ahead} commit(s) ahead of origin/{branch}")
    if behind:
        warnings.append(f"{behind} commit(s) behind origin/{branch}")
    if dirty:
        warnings.append("repo has uncommitted changes")
    missing = sum(1 for item in skill_items for value in item.status.values() if value in {"●", "~", "!"})
    if missing:
        warnings.append(f"{missing} skill link issue(s)")
    drift = sum(1 for item in mcp_items for value in item.status.values() if value in {"●", "~"})
    if drift:
        warnings.append(f"{drift} MCP config issue(s)")
    absent = sorted(
        {
            var
            for entry in servers.values()
            if entry.get("enabled", True)
            for value in list((entry.get("env") or {}).values())
            + list((entry.get("headers") or {}).values())
            for var in core.PLACEHOLDER.findall(str(value))
            if var not in os.environ
        }
    )
    if absent:
        warnings.append("env not set: " + ", ".join(absent))
    if not targets:
        warnings.append("no agent targets detected")

    return UiState(
        targets=targets,
        skills=skill_items,
        servers=mcp_items,
        repo=repo,
        warnings=warnings,
        state=state,
    )


def dashboard_markup(data: UiState) -> str:
    repo = data.repo
    lines: list[str] = []
    lines.append(
        f"[bold]{escape(core.REPO_ROOT.name)}[/bold]   "
        f"[cyan]{escape(repo['branch'])}[/cyan]   "
        f"{'↑' + repo['ahead'] if repo['ahead'] != '0' else ''}"
        f"{'↓' + repo['behind'] if repo['behind'] != '0' else ''}   "
        f"{'clean' if repo['dirty'] == 'no' else '[yellow]dirty[/yellow]'}   "
        f"targets {len(data.targets)}   skills {len(data.skills)}   "
        f"mcp {sum(1 for s in data.servers if s.entry.get('enabled', True))}/{len(data.servers)}"
    )
    lines.append("")
    lines.append("[bold]Attention[/bold]")
    if data.warnings:
        for warning in data.warnings:
            lines.append(f"  [yellow]![/yellow] {escape(warning)}")
    else:
        lines.append("  [green]✓[/green] everything in sync")

    lines.append("")
    lines.append("[bold]Targets[/bold]")
    for target in data.targets:
        skill_values = [s.status.get(target.name, "-") for s in data.skills]
        if target.skills_mode == "external":
            skill_text = "ext"
        else:
            good = sum(1 for v in skill_values if v == "✓")
            skill_text = f"{good}/{len(data.skills)}"
        mcp_values = [s.status.get(target.name, "-") for s in data.servers if s.entry.get("enabled", True)]
        if target.mcp_format is None:
            mcp_text = "—"
        else:
            good = sum(1 for v in mcp_values if v == "✓")
            mcp_text = f"{good}/{len(mcp_values)}"
        mark = "✓" if "●" not in skill_values and "~" not in skill_values and "●" not in mcp_values and "~" not in mcp_values else "!"
        location = "external via ~/.agents/skills" if target.skills_mode == "external" else str(target.skills_dir or "—")
        lines.append(
            f"  {mark} {target.name:<9} {escape(location):<30} {skill_text:<6} {mcp_text}"
        )

    lines.append("")
    lines.append("[bold]Repository[/bold]")
    lines.append(f"  branch   {escape(repo['branch'])}")
    lines.append(f"  head     {escape(repo['head'])}")
    lines.append(f"  remote   {repo['behind']} behind, {repo['ahead']} ahead")
    lines.append(f"  sync at  {escape(str(data.state.get('updated_at', 'never')))}")
    lines.append("")
    lines.append("[dim]s sync   u update   p prune   r refresh   ? help   q quit[/dim]")
    return "\n".join(lines)


def skill_detail(item: SkillItem) -> str:
    issues = [f"{name}={value}" for name, value in item.status.items() if value in {"●", "~", "!"}]
    lines = [
        f"[bold]{escape(item.name)}[/bold]  [dim]({escape(item.rel)})[/dim]",
        f"Category:    {escape(item.category)}",
        f"Description: {escape(item.description or '—')}",
        f"Source:      {escape(str(item.path / 'SKILL.md'))}",
    ]
    if issues:
        lines.append(f"[yellow]Issues:      {escape(', '.join(issues))}[/yellow]")
    else:
        lines.append("[green]Issues:      none[/green]")
    return "\n".join(lines)


def mcp_detail(item: McpItem) -> str:
    entry = item.entry
    kind = entry.get("transport", "stdio")
    if kind == "stdio":
        detail = " ".join([entry.get("command", ""), *entry.get("args", [])])
    else:
        detail = entry.get("url", "")
    lines = [
        f"[bold]{escape(item.name)}[/bold]  [dim]{escape(kind)} · {escape(item.scope)} · "
        f"{'on' if entry.get('enabled', True) else 'off'}[/dim]",
        f"Endpoint: {escape(detail)}",
    ]
    env = entry.get("env") or {}
    headers = entry.get("headers") or {}
    if env:
        rendered = []
        for key, value in env.items():
            value = str(value)
            match = core.PLACEHOLDER_FULL.match(value)
            if match:
                mark = "✓" if match.group(1) in os.environ else "✗"
                rendered.append(f"{key}=${{{match.group(1)}}} {mark}")
            else:
                rendered.append(f"{key}={value}")
        lines.append("Env:      " + "   ".join(rendered))
    if headers:
        rendered = []
        for key, value in headers.items():
            match = core.PLACEHOLDER_FULL.match(str(value))
            if match:
                mark = "✓" if match.group(1) in os.environ else "✗"
                rendered.append(f"{key}=${{{match.group(1)}}} {mark}")
            else:
                rendered.append(f"{key}=set")
        lines.append("Headers:  " + "   ".join(rendered))
    targets = entry.get("targets")
    lines.append(f"Targets:  {', '.join(targets) if targets else 'all'}")
    return "\n".join(lines)


def target_detail(target: Any, data: UiState) -> str:
    skill_values = [s.status.get(target.name, "-") for s in data.skills]
    mcp_values = [s.status.get(target.name, "-") for s in data.servers if s.entry.get("enabled", True)]
    skills = "external" if target.skills_mode == "external" else f"{sum(v == '✓' for v in skill_values)}/{len(skill_values)}"
    mcps = "—" if target.mcp_format is None else f"{sum(v == '✓' for v in mcp_values)}/{len(mcp_values)}"
    lines = [
        f"[bold]{escape(target.name)}[/bold]",
        f"Detected:   {'yes' if target.detected() else 'forced'}",
        f"Skills:     {escape(str(target.skills_dir or '—'))}  ({skills})",
        f"MCP:        {escape(str(target.mcp_config or '—'))}  ({mcps})",
    ]
    if target.detected() is False:
        lines.append("[yellow]Not installed; enabled by config or --target.[/yellow]")
    return "\n".join(lines)


class PreviewScreen(ModalScreen[bool]):
    BINDINGS = [
        Binding("a", "apply", "Apply"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, body: str, heading: str = "Preview", apply_label: str = "Apply") -> None:
        super().__init__()
        self.body = body
        self.heading = heading
        self.apply_label = apply_label

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label(self.heading, id="preview-title"),
            Static(self.body, id="preview-body"),
            Horizontal(
                Button(self.apply_label, id="apply", variant="primary"),
                Button("Cancel", id="cancel"),
                id="preview-buttons",
            ),
            id="preview-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "apply")

    def action_apply(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class MessageScreen(ModalScreen[None]):
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("enter", "close", "Close"),
    ]

    def __init__(self, body: str, heading: str = "Message") -> None:
        super().__init__()
        self.body = body
        self.heading = heading

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label(self.heading, id="preview-title"),
            Static(self.body, id="preview-body"),
            Horizontal(Button("Close", id="close", variant="primary"), id="preview-buttons"),
            id="preview-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close":
            self.dismiss(None)

    def action_close(self) -> None:
        self.dismiss(None)


class AgenthubApp(App[None]):
    CSS = """
    Screen { layout: vertical; }
    TabbedContent { height: 1fr; }
    TabPane { padding: 0 1; }
    DataTable { height: 1fr; }
    #skills-detail, #mcp-detail, #target-detail {
        height: auto;
        min-height: 8;
        max-height: 14;
        border: round $primary;
        padding: 0 1;
        margin-top: 1;
    }
    #dashboard, #doctor {
        height: 1fr;
        padding: 1 2;
        overflow-y: auto;
    }
    PreviewScreen, MessageScreen { align: center middle; }
    #preview-dialog {
        width: 92%;
        height: 88%;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    #preview-title { text-style: bold; }
    #preview-body { height: 1fr; overflow-y: auto; }
    #preview-buttons { height: auto; }
    #preview-buttons Button { margin-right: 1; }
    """

    BINDINGS = [
        Binding("1", "tab_dashboard", "Dashboard"),
        Binding("2", "tab_skills", "Skills"),
        Binding("3", "tab_mcp", "MCP"),
        Binding("4", "tab_targets", "Targets"),
        Binding("5", "tab_doctor", "Doctor"),
        Binding("s", "sync", "Sync"),
        Binding("u", "update", "Update"),
        Binding("r", "refresh", "Refresh"),
        Binding("e", "edit", "Edit"),
        Binding("space", "toggle_mcp", "Toggle MCP"),
        Binding("question_mark", "help", "Help"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.data: UiState | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(initial="tab-dashboard"):
            with TabPane("Dashboard", id="tab-dashboard"):
                yield Static(id="dashboard")
            with TabPane("Skills", id="tab-skills"):
                with Vertical():
                    yield DataTable(id="skills-table", cursor_type="row", zebra_stripes=True)
                    yield Static(id="skills-detail")
            with TabPane("MCP", id="tab-mcp"):
                with Vertical():
                    yield DataTable(id="mcp-table", cursor_type="row", zebra_stripes=True)
                    yield Static(id="mcp-detail")
            with TabPane("Targets", id="tab-targets"):
                with Vertical():
                    yield DataTable(id="targets-table", cursor_type="row", zebra_stripes=True)
                    yield Static(id="target-detail")
            with TabPane("Doctor", id="tab-doctor"):
                yield Static(id="doctor")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "agenthub"
        self.sub_title = str(core.REPO_ROOT.name)
        self.refresh_data()

    # -- data ---------------------------------------------------------

    def refresh_data(self) -> None:
        if not self.is_mounted:
            return
        try:
            self.data = collect()
        except SystemExit as exc:
            self.query_one("#dashboard", Static).update(
                f"[red]Cannot load agenthub state[/red]\n\n{escape(str(exc))}"
            )
            return
        except Exception as exc:  # noqa: BLE001
            self.query_one("#dashboard", Static).update(
                f"[red]Cannot load agenthub state[/red]\n\n{escape(str(exc))}"
            )
            return
        data = self.data
        self.query_one("#dashboard", Static).update(dashboard_markup(data))
        self._fill_skills(data)
        self._fill_mcp(data)
        self._fill_targets(data)
        code, output = capture(core.cmd_doctor, argparse.Namespace())
        self.query_one("#doctor", Static).update(output or "doctor produced no output")

    def _fill_skills(self, data: UiState) -> None:
        table = self.query_one("#skills-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Skill", "Category", *[target.name for target in data.targets])
        for item in data.skills:
            table.add_row(
                item.rel,
                item.category,
                *[item.status.get(target.name, "-") for target in data.targets],
                key=item.rel,
            )
        if data.skills:
            table.move_cursor(row=0)
            self._show_skill_detail(data.skills[0].rel)
        else:
            self.query_one("#skills-detail", Static).update("No skills found.")

    def _fill_mcp(self, data: UiState) -> None:
        table = self.query_one("#mcp-table", DataTable)
        mcp_targets = [target for target in data.targets if target.mcp_format is not None]
        table.clear(columns=True)
        table.add_columns("Server", "Type", "State", "Scope", *[target.name for target in mcp_targets])
        for item in data.servers:
            table.add_row(
                item.name,
                item.entry.get("transport", "stdio"),
                "on" if item.entry.get("enabled", True) else "off",
                item.scope,
                *[item.status.get(target.name, "-") for target in mcp_targets],
                key=item.name,
            )
        if data.servers:
            table.move_cursor(row=0)
            self._show_mcp_detail(data.servers[0].name)
        else:
            self.query_one("#mcp-detail", Static).update("No MCP servers in the catalog.")

    def _fill_targets(self, data: UiState) -> None:
        table = self.query_one("#targets-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Target", "Detected", "Skills dir", "MCP config", "Skills", "MCP")
        for target in data.targets:
            skill_values = [s.status.get(target.name, "-") for s in data.skills]
            mcp_values = [s.status.get(target.name, "-") for s in data.servers if s.entry.get("enabled", True)]
            skill_text = "ext" if target.skills_mode == "external" else f"{sum(v == '✓' for v in skill_values)}/{len(skill_values)}"
            mcp_text = "—" if target.mcp_format is None else f"{sum(v == '✓' for v in mcp_values)}/{len(mcp_values)}"
            table.add_row(
                target.name,
                "yes" if target.detected() else "forced",
                str(target.skills_dir or "—"),
                str(target.mcp_config or "—"),
                skill_text,
                mcp_text,
                key=target.name,
            )
        if data.targets:
            table.move_cursor(row=0)
            self._show_target_detail(data.targets[0].name)
        else:
            self.query_one("#target-detail", Static).update("No targets detected.")

    # -- detail -------------------------------------------------------

    def _show_skill_detail(self, rel: str) -> None:
        if not self.data:
            return
        item = next((s for s in self.data.skills if s.rel == rel), None)
        if item:
            self.query_one("#skills-detail", Static).update(skill_detail(item))

    def _show_mcp_detail(self, name: str) -> None:
        if not self.data:
            return
        item = next((s for s in self.data.servers if s.name == name), None)
        if item:
            self.query_one("#mcp-detail", Static).update(mcp_detail(item))

    def _show_target_detail(self, name: str) -> None:
        if not self.data:
            return
        target = next((t for t in self.data.targets if t.name == name), None)
        if target:
            self.query_one("#target-detail", Static).update(target_detail(target, self.data))

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        key = str(event.row_key.value)
        if event.data_table.id == "skills-table":
            self._show_skill_detail(key)
        elif event.data_table.id == "mcp-table":
            self._show_mcp_detail(key)
        elif event.data_table.id == "targets-table":
            self._show_target_detail(key)

    # -- shared helpers ----------------------------------------------

    def _tabs(self) -> TabbedContent:
        return self.query_one(TabbedContent)

    def _selected(self, table_id: str) -> str | None:
        table = self.query_one(f"#{table_id}", DataTable)
        if table.row_count == 0 or table.cursor_row < 0:
            return None
        row = table.get_row_at(table.cursor_row)
        return str(row[0]) if row else None

    def _sync_args(self, dry_run: bool) -> argparse.Namespace:
        return argparse.Namespace(
            target=None,
            dry_run=dry_run,
            force=False,
            prune=False,
            copy=False,
        )

    def _edit_path(self) -> Path | None:
        active = self._tabs().active
        if active == "tab-skills":
            rel = self._selected("skills-table")
            if rel and self.data:
                item = next((s for s in self.data.skills if s.rel == rel), None)
                if item:
                    return item.path / "SKILL.md"
        elif active == "tab-mcp":
            name = self._selected("mcp-table")
            if name and self.data:
                item = next((s for s in self.data.servers if s.name == name), None)
                if item:
                    return core.MCP_LOCAL if item.scope == "device" else core.MCP_CATALOG
        elif active == "tab-targets":
            name = self._selected("targets-table")
            if name and self.data:
                target = next((t for t in self.data.targets if t.name == name), None)
                if target:
                    return target.mcp_config or target.skills_dir
        return None

    def _open_editor(self, path: Path) -> None:
        editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "vi"
        try:
            with self.suspend():
                subprocess.call([*shlex.split(editor), str(path)])
        except Exception as exc:  # noqa: BLE001
            self.notify(f"Editor failed: {exc}", severity="error")
        self.refresh_data()

    # -- actions ------------------------------------------------------

    def action_tab_dashboard(self) -> None:
        self._tabs().active = "tab-dashboard"

    def action_tab_skills(self) -> None:
        self._tabs().active = "tab-skills"
        self.query_one("#skills-table", DataTable).focus()

    def action_tab_mcp(self) -> None:
        self._tabs().active = "tab-mcp"
        self.query_one("#mcp-table", DataTable).focus()

    def action_tab_targets(self) -> None:
        self._tabs().active = "tab-targets"
        self.query_one("#targets-table", DataTable).focus()

    def action_tab_doctor(self) -> None:
        self._tabs().active = "tab-doctor"

    def action_refresh(self) -> None:
        self.refresh_data()
        self.notify("Refreshed")

    def action_help(self) -> None:
        self.push_screen(MessageScreen(HELP_TEXT, "Help"))

    def action_edit(self) -> None:
        path = self._edit_path()
        if path is None:
            self.notify("Nothing editable on this screen", severity="warning")
            return
        self._open_editor(path)

    def action_sync(self) -> None:
        code, output = capture(core.cmd_sync, self._sync_args(dry_run=True))
        heading = "Sync preview" if code == 0 else "Sync preview (conflicts)"
        self.push_screen(
            PreviewScreen(f"$ agenthub sync --dry-run\n\n{output}", heading),
            self._after_sync_preview,
        )

    def _after_sync_preview(self, apply: bool | None) -> None:
        if not apply:
            return
        code, output = capture(core.cmd_sync, self._sync_args(dry_run=False))
        self.refresh_data()
        self.push_screen(MessageScreen(output or "(no output)", f"Sync result (exit {code})"))

    def action_update(self) -> None:
        data = self.data
        behind = data.repo.get("behind", "0") if data else "0"
        branch = data.repo.get("branch", "?") if data else "?"
        body = (
            f"Branch {branch} is {behind} commit(s) behind its upstream.\n\n"
            "This runs `git pull --ff-only`, then syncs every detected target.\n"
            "Local uncommitted changes must be committed or stashed first.\n"
        )
        self.push_screen(
            PreviewScreen(body, "Update from origin", apply_label="Pull & sync"),
            self._after_update_preview,
        )

    def _after_update_preview(self, apply: bool | None) -> None:
        if apply:
            self._update_worker()

    @work(thread=True, exclusive=True)
    def _update_worker(self) -> None:
        code, output = capture(core.cmd_update, self._sync_args(dry_run=False))
        self.app.call_from_thread(self._update_done, code, output)

    def _update_done(self, code: int, output: str) -> None:
        self.refresh_data()
        self.push_screen(MessageScreen(output or "(no output)", f"Update result (exit {code})"))

    def action_toggle_mcp(self) -> None:
        if self._tabs().active != "tab-mcp":
            self.notify("Switch to the MCP tab to toggle a server", severity="warning")
            return
        name = self._selected("mcp-table")
        if not name or not self.data:
            return
        item = next((s for s in self.data.servers if s.name == name), None)
        if not item:
            return
        enabled = bool(item.entry.get("enabled", True))
        path = core.set_local_mcp_enabled(name, not enabled)
        self.notify(f"{name}: {'off' if enabled else 'on'} for this device ({path.name})")
        args = self._sync_args(dry_run=False)
        args.prune = True
        code, output = capture(core.cmd_sync, args)
        self.refresh_data()
        self.push_screen(MessageScreen(output or "(no output)", f"Sync result (exit {code})"))


def run() -> int:
    AgenthubApp().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
