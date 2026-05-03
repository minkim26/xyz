from __future__ import annotations

import asyncio
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Static

try:
    from xyz.managers import Package, ManagerRegistry
    from xyz.ai import explain_package, assess_orphan_risk
except ImportError:
    from managers import Package, ManagerRegistry  # type: ignore[no-redef]
    from ai import explain_package, assess_orphan_risk  # type: ignore[no-redef]


# ---------------------------------------------------------------------------
# Detail pane
# ---------------------------------------------------------------------------

class DetailPane(Static):
    DEFAULT_CSS = """
    DetailPane {
        padding: 1 2;
        height: 100%;
        background: $panel;
    }
    """

    def show_loading(self) -> None:
        self.update("[dim]Scanning package managers…[/dim]")

    def show_empty(self) -> None:
        self.update("[dim]Select a package to see details.[/dim]")

    def show_package(self, pkg: Package, ai_text: str = "") -> None:
        orphan_badge = "\n[yellow bold]⚠  Orphaned[/yellow bold]" if pkg.is_orphan else ""
        if ai_text:
            ai_block = f"\n\n[bold cyan]AI Explanation[/bold cyan]\n{ai_text}"
        else:
            ai_block = "\n\n[bold cyan]AI Explanation[/bold cyan]\n[dim]Loading…[/dim]"

        self.update(
            f"[bold white]{pkg.name}[/bold white]\n"
            f"[dim]{'─' * 30}[/dim]\n"
            f"Version    {pkg.version}\n"
            f"Manager    {pkg.manager}\n"
            f"Size       {pkg.size}"
            f"{orphan_badge}"
            f"{ai_block}"
        )


# ---------------------------------------------------------------------------
# Delete confirmation modal
# ---------------------------------------------------------------------------

class ConfirmDeleteModal(ModalScreen[bool]):
    DEFAULT_CSS = """
    ConfirmDeleteModal {
        align: center middle;
    }
    #modal-box {
        width: 58;
        height: auto;
        border: thick $error;
        background: $surface;
        padding: 1 2;
    }
    #modal-title {
        text-align: center;
        color: $error;
        text-style: bold;
        margin-bottom: 1;
    }
    #modal-pkg {
        text-align: center;
        margin-bottom: 1;
    }
    #modal-hint {
        text-align: center;
        margin-bottom: 1;
    }
    #modal-buttons {
        layout: horizontal;
        align: center middle;
        height: 3;
    }
    #modal-buttons Button {
        margin: 0 2;
    }
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
    TITLE = "XYZ"
    SUB_TITLE = "Universal Dependency Manager"

    BINDINGS = [
        Binding("u",      "update_package", "Update",      show=True),
        Binding("d",      "delete_package", "Delete",      show=True),
        Binding("U",      "upgrade_all",    "Upgrade All", show=True),
        Binding("o",      "toggle_orphans", "Orphans",     show=True),
        Binding("m",      "cycle_manager",  "Manager",     show=True),
        Binding("/",      "focus_search",   "Search",      show=True),
        Binding("escape", "blur_search",    "Back",        show=False),
        Binding("q",      "quit",           "Quit",        show=True),
    ]

    DEFAULT_CSS = """
    Screen {
        layout: vertical;
    }

    #search-row {
        height: 3;
        padding: 0 1;
        background: $panel;
        border-bottom: solid $primary;
    }

    #search-input {
        width: 1fr;
    }

    #filter-label {
        width: 22;
        content-align: center middle;
        color: $accent;
        text-style: bold;
        padding: 0 1;
    }

    #main-row {
        height: 1fr;
    }

    #package-list {
        width: 2fr;
        border-right: solid $primary;
    }

    #detail-scroll {
        width: 1fr;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._managers_registry = ManagerRegistry()
        self._all_packages: list[Package] = []
        self._filtered: list[Package] = []
        self._selected: Optional[Package] = None
        self._orphan_only: bool = False
        self._manager_filter: Optional[str] = None
        self._managers: list[str] = []
        self._ai_task: Optional[asyncio.Task] = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="search-row"):
            yield Input(placeholder="Search packages…", id="search-input")
            yield Label("All managers", id="filter-label")
        with Horizontal(id="main-row"):
            yield DataTable(id="package-list", cursor_type="row", zebra_stripes=True)
            yield DetailPane(id="detail-scroll")
        yield Footer()

    async def on_mount(self) -> None:
        table = self.query_one("#package-list", DataTable)
        table.add_columns("Name", "Manager", "Version", "Size", "")
        self.query_one(DetailPane).show_loading()
        self.run_worker(self._load_packages())

    # ── loading ──────────────────────────────────────────────────────────────

    async def _load_packages(self) -> None:
        packages = await self._managers_registry.scan_all()
        self._all_packages = packages
        self._managers = sorted({p.manager for p in packages})
        self._apply_filters()

    # ── filtering & table ────────────────────────────────────────────────────

    def _apply_filters(self) -> None:
        pkgs = list(self._all_packages)

        if self._orphan_only:
            pkgs = [p for p in pkgs if p.is_orphan]

        if self._manager_filter:
            pkgs = [p for p in pkgs if p.manager == self._manager_filter]

        query = self.query_one("#search-input", Input).value.strip().lower()
        if query and not query.startswith("?"):
            pkgs = [p for p in pkgs if query in p.name.lower()]

        self._filtered = pkgs
        self._rebuild_table()

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
        if not self._filtered:
            detail.show_empty()
            self._selected = None
            return

        table.move_cursor(row=0)

    # ── selection ────────────────────────────────────────────────────────────

    def _select_row(self, row: int) -> None:
        if not (0 <= row < len(self._filtered)):
            return
        pkg = self._filtered[row]
        self._selected = pkg
        self.query_one(DetailPane).show_package(pkg)
        self._kick_ai(pkg)

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
                self.query_one(DetailPane).show_package(pkg, ai_text=text)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            if self._selected and self._selected.name == pkg.name:
                self.query_one(DetailPane).show_package(pkg, ai_text=f"[red]AI error: {exc}[/red]")

    # ── events ───────────────────────────────────────────────────────────────

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._select_row(event.cursor_row)

    def on_input_changed(self, _: Input.Changed) -> None:
        self._apply_filters()

    # ── actions ──────────────────────────────────────────────────────────────

    def action_focus_search(self) -> None:
        self.query_one("#search-input", Input).focus()

    def action_blur_search(self) -> None:
        inp = self.query_one("#search-input", Input)
        if inp.value:
            inp.value = ""
        else:
            self.query_one("#package-list", DataTable).focus()

    def action_toggle_orphans(self) -> None:
        self._orphan_only = not self._orphan_only
        self._update_filter_label()
        self._apply_filters()

    def action_cycle_manager(self) -> None:
        options: list[Optional[str]] = [None] + self._managers
        try:
            idx = options.index(self._manager_filter)
        except ValueError:
            idx = 0
        self._manager_filter = options[(idx + 1) % len(options)]
        self._update_filter_label()
        self._apply_filters()

    def _update_filter_label(self) -> None:
        parts: list[str] = []
        if self._orphan_only:
            parts.append("[yellow]orphans[/yellow]")
        if self._manager_filter:
            parts.append(self._manager_filter)
        label_text = " · ".join(parts) if parts else "All managers"
        self.query_one("#filter-label", Label).update(label_text)

    def action_update_package(self) -> None:
        if not self._selected:
            self.notify("No package selected.", severity="warning")
            return
        self.notify(
            f"Updating [bold]{self._selected.name}[/bold]…",
            title="Update",
        )
        # TODO: await self._managers_registry.update(self._selected)

    async def action_delete_package(self) -> None:
        if not self._selected:
            self.notify("No package selected.", severity="warning")
            return
        confirmed: bool = await self.push_screen_wait(ConfirmDeleteModal(self._selected))
        if confirmed:
            pkg = self._selected
            self.notify(
                f"Deleting [bold]{pkg.name}[/bold]…",
                title="Delete",
                severity="warning",
            )
            # TODO: await self._managers_registry.delete(pkg)
            self._all_packages = [p for p in self._all_packages if p.name != pkg.name]
            self._apply_filters()

    def action_upgrade_all(self) -> None:
        count = len(self._all_packages)
        self.notify(
            f"Upgrading {count} packages across all managers…",
            title="Upgrade All",
        )
        # TODO: await self._managers_registry.upgrade_all()


def main() -> None:
    XYZApp().run()


if __name__ == "__main__":
    main()
