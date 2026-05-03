from __future__ import annotations

import asyncio
from collections import Counter
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Static

from xyz.managers import Package, ManagerRegistry

try:
    from xyz.managers import Package, ManagerRegistry
    from xyz.ai import explain_package, assess_orphan_risk, natural_language_search
except ImportError:
    from managers import Package, ManagerRegistry  # type: ignore[no-redef]
    from ai import explain_package, assess_orphan_risk, natural_language_search  # type: ignore[no-redef]


# ---------------------------------------------------------------------------
# Detail pane
# ---------------------------------------------------------------------------

class DetailPane(Widget):
    DEFAULT_CSS = """
    DetailPane {
        height: 100%;
        background: $panel;
        overflow-y: auto;
    }
    """

    def show_loading(self) -> None:
        self.update("[dim]Scanning package managers…[/dim]")

    def show_empty(self) -> None:
        self.update("[dim]Select a package to see details.[/dim]")

    def show_package(self, pkg: Package, ai_text: str = "", ai_loading: bool = False) -> None:
        orphan_badge = "\n[yellow bold]⚠  Orphaned[/yellow bold]" if pkg.is_orphan else ""
        if ai_text:
            ai_block = f"\n\n[bold cyan]AI Explanation[/bold cyan]\n{ai_text}"
        elif ai_loading:
            ai_block = "\n\n[bold cyan]AI Explanation[/bold cyan]\n[dim]Loading…[/dim]"
        else:
            ai_block = "\n\n[bold cyan]AI Explanation[/bold cyan]\n[dim]Press 'a' to generate insights[/dim]"

        self.query_one("#dp-header", Static).update(
            f"[bold white]{pkg.name}[/bold white]  "
            f"[dim]{pkg.version}[/dim]"
            f"  [{color}]{pkg.manager}[/{color}]"
            f"{badge_str}"
        )
        self.query_one("#dp-meta", Static).update(
            f"[dim]size[/dim]  {pkg.size}"
        )
        ai_block = (
            f"[bold cyan]● GEMINI[/bold cyan]\n\n{ai_text}"
            if ai_text
            else "[bold cyan]● GEMINI[/bold cyan]\n\n[dim]Loading…[/dim]"
        )
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
        Binding("u",      "update_package", "Update",      show=True),
        Binding("d",      "delete_package", "Delete",      show=True),
        Binding("U",      "upgrade_all",    "Upgrade All", show=True),
        Binding("o",      "toggle_orphans", "Orphans",     show=True),
        Binding("m",      "cycle_manager",  "Manager",     show=True),
        Binding("a",      "ask_ai",         "Ask AI",      show=True),
        Binding("/",      "focus_search",   "Search",      show=True),
        Binding("escape", "blur_search",    "Back",        show=False),
        Binding("q",      "quit",           "Quit",        show=True),
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
        # Package | None where None = separator row
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
            "↑↓ navigate   u update   d delete   o orphans   tab filter   / search   q quit",
            id="key-bar",
        )

    async def on_mount(self) -> None:
        table = self.query_one("#package-list", DataTable)
        table.add_columns("PACKAGE  VERSION", "MANAGER", "SIZE", "STATUS")
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
        for pkg in self._filtered:
            tag = "[yellow]orphan[/yellow]" if pkg.is_orphan else ""
            table.add_row(
                pkg.name,
                pkg.manager,
                pkg.version,
                pkg.formatted_size(),
                tag,
                key=pkg.name,
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
            return  # separator — ignore
        self._selected = pkg
        
        # Cancel any previous AI task that might still be running
        if self._ai_task and not self._ai_task.done():
            self._ai_task.cancel()
            
        # Just show the basic package details (wait for manual AI trigger)
        self.query_one(DetailPane).show_package(pkg)

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
        if event.input.id == "search-input":
            query = event.value.strip()
            if query.startswith("?"):
                self.query_one(DetailPane).update("[dim]Asking Gemini to find packages...[/dim]")
                package_names = [p.name for p in self._all_packages]
                
                try:
                    matches = await natural_language_search(query[1:].strip(), package_names)
                    self._filtered = [p for p in self._all_packages if p.name in matches]
                    self._rebuild_table()
                    
                    if matches:
                        self.query_one(DetailPane).update(f"[bold cyan]AI Search Found {len(matches)} matches![/bold cyan]\nSelect one to view details.")
                    else:
                        self.query_one(DetailPane).update("[yellow]AI could not find any relevant packages.[/yellow]")
                except Exception as e:
                    self.query_one(DetailPane).update(f"[red]AI Search Error: {e}[/red]")

    # ── actions ──────────────────────────────────────────────────────────────

    def action_focus_search(self) -> None:
        self.query_one("#search-input", Input).focus()

    def action_ask_ai(self) -> None:
        if not self._selected:
            self.notify("No package selected.", severity="warning")
            return
            
        # Update UI to show loading state
        self.query_one(DetailPane).show_package(self._selected, ai_loading=True)
        self._kick_ai(self._selected)

    def action_blur_search(self) -> None:
        inp = self.query_one("#search-input", Input)
        if inp.value:
            inp.value = ""
        else:
            self.query_one("#package-list", DataTable).focus()

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
