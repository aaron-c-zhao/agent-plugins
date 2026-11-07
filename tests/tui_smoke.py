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
"""Headless smoke test for the agenthub TUI."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agenthub_tui import AgenthubApp, MessageScreen, PreviewScreen  # noqa: E402
from textual.widgets import DataTable, TabbedContent  # noqa: E402


async def main() -> None:
    app = AgenthubApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        tabs = app.query_one(TabbedContent)
        assert tabs.active == "tab-dashboard"
        assert app.query_one("#dashboard").content

        await pilot.press("2")
        await pilot.pause()
        assert tabs.active == "tab-skills"
        assert app.query_one("#skills-table", DataTable).row_count > 0

        await pilot.press("3")
        await pilot.pause()
        assert tabs.active == "tab-mcp"

        await pilot.press("4")
        await pilot.pause()
        assert tabs.active == "tab-targets"

        await pilot.press("5")
        await pilot.pause()
        assert tabs.active == "tab-doctor"

        await pilot.press("s")
        await pilot.pause()
        assert isinstance(app.screen, PreviewScreen)
        assert "agenthub sync" in app.screen.body
        await pilot.press("escape")
        await pilot.pause()

        await pilot.press("question_mark")
        await pilot.pause()
        assert isinstance(app.screen, MessageScreen)
        await pilot.press("escape")
        await pilot.pause()

        app.exit()


if __name__ == "__main__":
    asyncio.run(main())
    print("tui smoke test passed")
