from __future__ import annotations

import asyncio
from collections import Counter
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Static

from xyz.managers import Package, ManagerRegistry

try:
    from xyz.ai import explain_package, assess_orphan_risk, natural_language_search
except ImportError:
    async def explain_package(_name: str, _manager: str, _version: str) -> str:  # type: ignore[misc]
        return "AI unavailable — check GEMINI_API_KEY and dependencies."
    async def assess_orphan_risk(_name: str, _manager: str) -> str:  # type: ignore[misc]
        return "AI unavailable — check GEMINI_API_KEY and dependencies."
    async def natural_language_search(_query: str, _package_names: list[str]) -> list[str]:  # type: ignore[misc]
        return []


MANAGER_COLORS: dict[str, str] = {
    "pip":    "#3B82F6",
    "npm":    "#22C55E",
    "brew":   "#EF4444",
    "apt":    "#EAB308",
    "bun":    "#F97316",
    "pacman": "#A855F7",
}

def _mgr_color(manager: str) -> str:
    return MANAGER_COLORS.get(manager.lower(), "#9CA3AF")

def _status_markup(pkg: Package, dupe_names: set[str]) -> str:
    if pkg.is_orphan:
        return "[bold red]orphan[/bold red]"
    if pkg.name in dupe_names:
        return "[yellow]⚠ dupe[/yellow]"
    return "[dim green]✓ ok[/dim green]"


# ---------------------------------------------------------------------------
# Detail pane
# ---------------------------------------------------------------------------

class DetailPane(Widget):
    DEFAULT_CSS = """
    DetailPane {
        height: 100%;
        background: $panel;
    }
    #dp-header {
        padding: 1 2 0 2;
        height: auto;
        border-bottom: solid $surface;
    }
    #dp-meta {
        padding: 1 2;
        height: auto;
        border-bottom: solid $surface;
    }
    #dp-actions {
        padding: 1 2;
        height: 5;
        border-bottom: solid $surface;
        align: left middle;
    }
    #dp-actions Button {
        margin-right: 1;
        min-width: 14;
    }
    #dp-ai-scroll {
        height: 1fr;
    }
    #dp-ai {
        padding: 1 2;
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("", id="dp-header")
        yield Static("", id="dp-meta")
        with Horizontal(id="dp-actions"):
            yield Button("↑  update", id="btn-detail-update", variant="primary")
            yield Button("✕  remove", id="btn-detail-remove", variant="error")
        with VerticalScroll(id="dp-ai-scroll"):
            yield Static("", id="dp-ai")

    def on_mount(self) -> None:
        self.show_empty()

    def show_empty(self, msg: str = "Select a package to see details.") -> None:
        self.query_one("#dp-header", Static).update(f"[dim]{msg}[/dim]")
        self.query_one("#dp-meta", Static).update("")
        self.query_one("#dp-ai", Static).update("")
        self.query_one("#dp-actions").display = False

    def show_package(
        self,
        pkg: Package,
        dupe_names: set[str],
        ai_text: str = "",
        ai_loading: bool = False,
    ) -> None:
        color = _mgr_color(pkg.manager)
        badges: list[str] = []
        if pkg.is_orphan:
            badges.append("[bold red]orphan[/bold red]")
        if pkg.name in dupe_names:
            badges.append("[yellow]⚠ dupe[/yellow]")
        badge_str = "  " + "  ".join(badges) if badges else ""

        self.query_one("#dp-header", Static).update(
            f"[bold white]{pkg.name}[/bold white]  "
            f"[dim]{pkg.version}[/dim]"
            f"  [{color}]{pkg.manager}[/{color}]"
            f"{badge_str}"
        )
        self.query_one("#dp-meta", Static).update(
            f"[dim]manager[/dim]  [{color}]{pkg.manager}[/{color}]  "
            f"[dim]version[/dim]  {pkg.version}"
        )

        if ai_text:
            ai_block = f"[bold cyan]● GEMINI[/bold cyan]\n\n{ai_text}"
        elif ai_loading:
            ai_block = "[bold cyan]● GEMINI[/bold cyan]\n\n[dim]Loading…[/dim]"
        else:
            ai_block = "[bold cyan]● GEMINI[/bold cyan]\n\n[dim]Press 'a' for AI insights[/dim]"

        self.query_one("#dp-ai", Static).update(ai_block)
        self.query_one("#dp-actions").display = True


# ---------------------------------------------------------------------------
# Delete confirmation modal
# ---------------------------------------------------------------------------

class ConfirmDeleteModal(ModalScreen[bool]):
    DEFAULT_CSS = """
    ConfirmDeleteModal { align: center middle; }
    #modal-box {
        width: 58; height: auto;
        border: thick $error; background: $surface; padding: 1 2;
    }
    #modal-title { text-align: center; color: $error; text-style: bold; margin-bottom: 1; }
    #modal-pkg   { text-align: center; margin-bottom: 1; }
    #modal-hint  { text-align: center; margin-bottom: 1; }
    #modal-buttons { layout: horizontal; align: center middle; height: 3; }
    #modal-buttons Button { margin: 0 2; }
    """

    def __init__(self, pkg: Package) -> None:
        super().__init__()
        self.pkg = pkg

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-box"):
            yield Label("Delete Package", id="modal-title")
            yield Label(
                f"[white]{self.pkg.name}[/white]  "
                f"[dim]{self.pkg.manager} {self.pkg.version}[/dim]",
                id="modal-pkg",
            )
            yield Label("[dim]This action cannot be undone.[/dim]", id="modal-hint")
            with Horizontal(id="modal-buttons"):
                yield Button("Cancel", variant="default", id="btn-cancel")
                yield Button("Delete", variant="error", id="btn-confirm")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "btn-confirm")


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

class XYZApp(App):
    TITLE = "xyz — dependency manager"

    BINDINGS = [
        Binding("u",      "update_package", "u update",      show=False),
        Binding("d",      "delete_package", "d delete",      show=False),
        Binding("U",      "upgrade_all",    "U upgrade all", show=False),
        Binding("o",      "toggle_orphans", "o orphans",     show=False),
        Binding("m",      "cycle_manager",  "m manager",     show=False),
        Binding("a",      "ask_ai",         "a AI",          show=False),
        Binding("/",      "focus_search",   "/ search",      show=False),
        Binding("escape", "blur_search",    "esc back",      show=False),
        Binding("q",      "quit",           "q quit",        show=False),
    ]

    DEFAULT_CSS = """
    Screen { layout: vertical; }

    /* ── search bar ── */
    #search-row {
        height: 5;
        padding: 0 1;
        background: $panel;
        border-bottom: solid $primary-darken-2;
        align: left middle;
    }
    #search-label {
        width: 8;
        color: $text-muted;
        text-style: bold;
        padding: 0 1;
    }
    #search-input {
        width: 1fr;
        background: $surface;
        border: tall $primary-darken-2;
    }
    #result-count {
        width: auto;
        min-width: 12;
        color: $text-muted;
        padding: 0 1;
    }
    #manager-pills {
        width: auto;
        height: 5;
        align: left middle;
    }
    .manager-pill {
        height: 3;
        min-width: 5;
        border: none;
        margin: 0 0 0 1;
        background: $surface;
    }
    .pill-active { text-style: bold reverse; }

    /* per-manager pill colours */
    #pill-pip    { color: #3B82F6; }
    #pill-npm    { color: #22C55E; }
    #pill-brew   { color: #EF4444; }
    #pill-apt    { color: #EAB308; }
    #pill-bun    { color: #F97316; }
    #pill-pacman { color: #A855F7; }

    /* ── main panels ── */
    #main-row { height: 1fr; }
    #package-list {
        width: 2fr;
        border-right: solid $primary-darken-2;
    }
    #detail-pane { width: 1fr; }

    /* ── bottom stats bar ── */
    #stats-bar {
        height: 1;
        background: $panel;
        border-top: solid $primary-darken-2;
        padding: 0 1;
        color: $text-muted;
        text-align: right;
    }

    /* ── custom footer ── */
    #key-bar {
        height: 1;
        background: $panel;
        padding: 0 1;
        color: $text-muted;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._managers_registry = ManagerRegistry()
        self._all_packages: list[Package] = []
        self._display_rows: list[Package | None] = []
        self._dupe_names: set[str] = set()
        self._selected: Optional[Package] = None
        self._orphan_only: bool = False
        self._manager_filter: Optional[str] = None
        self._managers: list[str] = []
        self._ai_task: Optional[asyncio.Task] = None

    def compose(self) -> ComposeResult:
        with Horizontal(id="search-row"):
            yield Label("search", id="search-label")
            yield Input(placeholder="", id="search-input")
            yield Label("", id="result-count")
            yield Horizontal(id="manager-pills")
        with Horizontal(id="main-row"):
            yield DataTable(id="package-list", cursor_type="row", zebra_stripes=True)
            yield DetailPane(id="detail-pane")
        yield Static("", id="stats-bar")
        yield Static(
            "↑↓ navigate   u update   d delete   a AI   o orphans   m manager   / search   q quit",
            id="key-bar",
        )

    async def on_mount(self) -> None:
        table = self.query_one("#package-list", DataTable)
        table.add_columns("PACKAGE", "VERSION", "MANAGER", "STATUS")
        self.query_one(DetailPane).show_empty("Scanning package managers…")
        self.run_worker(self._load_packages())

    # ── loading ──────────────────────────────────────────────────────────────

    async def _load_packages(self) -> None:
        packages = await self._managers_registry.scan_all()
        self._all_packages = packages
        self._managers = sorted({p.manager for p in packages})
        name_counts = Counter(p.name for p in packages)
        self._dupe_names = {n for n, c in name_counts.items() if c > 1}
        self._mount_pills()
        self._apply_filters()

    def _mount_pills(self) -> None:
        container = self.query_one("#manager-pills")
        for manager in self._managers:
            container.mount(Button(manager, id=f"pill-{manager}", classes="manager-pill"))

    # ── filtering ────────────────────────────────────────────────────────────

    def _apply_filters(self) -> None:
        pkgs = list(self._all_packages)
        if self._orphan_only:
            pkgs = [p for p in pkgs if p.is_orphan]
        if self._manager_filter:
            pkgs = [p for p in pkgs if p.manager == self._manager_filter]

        query = self.query_one("#search-input", Input).value.strip().lower()
        if query and not query.startswith("?"):
            matched = [p for p in pkgs if query in p.name.lower()]
            self._display_rows = matched
            self.query_one("#result-count", Label).update(f"{len(matched)} results")
        else:
            self._display_rows = pkgs
            self.query_one("#result-count", Label).update("")

        self._rebuild_table()
        self._update_stats()

    def _rebuild_table(self) -> None:
        table = self.query_one("#package-list", DataTable)
        table.clear()

        for item in self._display_rows:
            if item is None:
                table.add_row("[dim]─── other packages[/dim]", "", "", "", key="__sep__")
            else:
                pkg = item
                color = _mgr_color(pkg.manager)
                table.add_row(
                    pkg.name,
                    f"[dim]{pkg.version}[/dim]",
                    f"[{color}]{pkg.manager}[/{color}]",
                    _status_markup(pkg, self._dupe_names),
                    key=f"{pkg.manager}:{pkg.name}",
                )

        detail = self.query_one(DetailPane)
        real_rows = [r for r in self._display_rows if r is not None]
        if not real_rows:
            detail.show_empty("No packages match.")
            self._selected = None
            return

        first_real = next(i for i, r in enumerate(self._display_rows) if r is not None)
        table.move_cursor(row=first_real)

    def _update_stats(self) -> None:
        total   = len(self._all_packages)
        mgrs    = len(self._managers)
        orphans = sum(1 for p in self._all_packages if p.is_orphan)
        self.query_one("#stats-bar", Static).update(
            f"{total} packages  ·  {mgrs} managers  ·  {orphans} orphans"
        )

    # ── selection ────────────────────────────────────────────────────────────

    def _select_row(self, row: int) -> None:
        if not (0 <= row < len(self._display_rows)):
            return
        pkg = self._display_rows[row]
        if pkg is None:
            return
        self._selected = pkg
        if self._ai_task and not self._ai_task.done():
            self._ai_task.cancel()
        self.query_one(DetailPane).show_package(pkg, self._dupe_names)

    def _kick_ai(self, pkg: Package) -> None:
        if self._ai_task and not self._ai_task.done():
            self._ai_task.cancel()
        self._ai_task = asyncio.create_task(self._fetch_ai(pkg))

    async def _fetch_ai(self, pkg: Package) -> None:
        try:
            if pkg.is_orphan:
                text = await assess_orphan_risk(pkg.name, pkg.manager)
            else:
                text = await explain_package(pkg.name, pkg.manager, pkg.version)
            if self._selected and self._selected.name == pkg.name:
                self.query_one(DetailPane).show_package(pkg, self._dupe_names, ai_text=text)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            if self._selected and self._selected.name == pkg.name:
                self.query_one(DetailPane).show_package(
                    pkg, self._dupe_names, ai_text=f"[red]Error: {exc}[/red]"
                )

    # ── events ───────────────────────────────────────────────────────────────

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._select_row(event.cursor_row)

    def on_input_changed(self, _: Input.Changed) -> None:
        self._apply_filters()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "search-input":
            return
        query = event.value.strip()
        if not query.startswith("?"):
            return
        self.query_one(DetailPane).show_empty("Asking Gemini…")
        try:
            package_names = [p.name for p in self._all_packages]
            matches = await natural_language_search(query[1:].strip(), package_names)
            matched_pkgs = [p for p in self._all_packages if p.name in matches]
            self._display_rows = matched_pkgs
            self._rebuild_table()
            self.query_one("#result-count", Label).update(f"{len(matched_pkgs)} results")
            if not matched_pkgs:
                self.query_one(DetailPane).show_empty("No AI matches found.")
        except Exception as exc:
            self.query_one(DetailPane).show_empty(f"AI search error: {exc}")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id.startswith("pill-"):
            self._toggle_pill(btn_id[5:])
            event.stop()
        elif btn_id == "btn-detail-update":
            self.action_update_package()
            event.stop()
        elif btn_id == "btn-detail-remove":
            await self.action_delete_package()
            event.stop()

    # ── actions ──────────────────────────────────────────────────────────────

    def action_focus_search(self) -> None:
        self.query_one("#search-input", Input).focus()

    def action_blur_search(self) -> None:
        inp = self.query_one("#search-input", Input)
        if inp.value:
            inp.value = ""
        else:
            self.query_one("#package-list", DataTable).focus()

    def action_ask_ai(self) -> None:
        if not self._selected:
            self.notify("No package selected.", severity="warning")
            return
        self.query_one(DetailPane).show_package(
            self._selected, self._dupe_names, ai_loading=True
        )
        self._kick_ai(self._selected)

    def action_toggle_orphans(self) -> None:
        self._orphan_only = not self._orphan_only
        self._apply_filters()

    def action_cycle_manager(self) -> None:
        options: list[Optional[str]] = [None] + self._managers
        try:
            idx = options.index(self._manager_filter)
        except ValueError:
            idx = 0
        self._manager_filter = options[(idx + 1) % len(options)]
        self._update_pill_styles()
        self._apply_filters()

    def _update_pill_styles(self) -> None:
        for mgr in self._managers:
            try:
                btn = self.query_one(f"#pill-{mgr}", Button)
                if self._manager_filter == mgr:
                    btn.add_class("pill-active")
                else:
                    btn.remove_class("pill-active")
            except Exception:
                pass

    def _toggle_pill(self, manager: str) -> None:
        self._manager_filter = None if self._manager_filter == manager else manager
        self._update_pill_styles()
        self._apply_filters()

    def action_update_package(self) -> None:
        if not self._selected:
            self.notify("No package selected.", severity="warning")
            return
        self.notify(f"Updating [bold]{self._selected.name}[/bold]…", title="Update")
        # TODO: await self._managers_registry.update(self._selected)

    async def action_delete_package(self) -> None:
        if not self._selected:
            self.notify("No package selected.", severity="warning")
            return
        confirmed: bool = await self.push_screen_wait(ConfirmDeleteModal(self._selected))
        if confirmed:
            pkg = self._selected
            self.notify(f"Deleting [bold]{pkg.name}[/bold]…", title="Delete", severity="warning")
            # TODO: await self._managers_registry.delete(pkg)
            self._all_packages = [p for p in self._all_packages if p.name != pkg.name]
            self._apply_filters()

    def action_upgrade_all(self) -> None:
        self.notify(
            f"Upgrading {len(self._all_packages)} packages across all managers…",
            title="Upgrade All",
        )
        # TODO: await self._managers_registry.upgrade_all()


def main() -> None:
    XYZApp().run()


if __name__ == "__main__":
    main()
