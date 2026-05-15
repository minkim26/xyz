from __future__ import annotations

import asyncio
import re
import subprocess
from collections import Counter
from typing import Optional, Sequence, Any, AsyncGenerator

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, Static

from xyz.managers import Package, ManagerRegistry

try:
    from mermaid_ascii import _resolve_binary as _mermaid_binary
    _MERMAID_BIN: str | None = _mermaid_binary()
except Exception:
    _MERMAID_BIN = None


def _build_mermaid(name: str, requires: list[str], required_by: list[str]) -> str:
    def safe(s: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]", "_", s)
    lines = ["graph LR"]
    pkg = safe(name)
    for dep in requires:
        lines.append(f"    {pkg} --> {safe(dep)}")
    for rev in required_by:
        lines.append(f"    {safe(rev)} --> {pkg}")
    if not requires and not required_by:
        lines.append(f"    {pkg}[{name}]")
    return "\n".join(lines)


async def _render_graph(mermaid_str: str) -> str:
    if not _MERMAID_BIN:
        return ""
    result = await asyncio.to_thread(
        subprocess.run,
        [_MERMAID_BIN],
        input=mermaid_str.encode("utf-8"),
        capture_output=True,
    )
    if result.returncode != 0:
        return f"[red]Mermaid Error:[/red]\n{result.stderr.decode('utf-8', errors='replace').strip()}"
    return result.stdout.decode("utf-8", errors="replace").strip()

try:
    from xyz.ai import (
        stream_explain_package, stream_assess_orphan_risk,
        natural_language_search, smart_cleanup, check_package_cves,
    )
except ImportError:
    async def stream_explain_package(name: str, manager: str, version: str) -> AsyncGenerator[str, None]:
        yield "AI unavailable — check GEMINI_API_KEY and dependencies."
    async def stream_assess_orphan_risk(name: str, manager: str) -> AsyncGenerator[str, None]:
        yield "AI unavailable — check GEMINI_API_KEY and dependencies."
    async def natural_language_search(query: str, package_names: list[str]) -> list[str]:
        return []
    async def smart_cleanup(packages: list[dict[str, Any]], dupe_names: set[str] | None = None) -> list[dict[str, Any]]:
        return []
    async def check_package_cves(name: str, manager: str, version: str) -> dict[str, Any]:
        return {"severity": "unknown", "cve_ids": [], "summary": "AI unavailable."}


# Breathing animation chars + matching Gemini-brand color gradient (blue→violet→fuchsia→back)
_SPINNER_CHARS  = ["•",       "✦",       "✦",       "✧",       "✦",       "✦",       "✧",       "•"      ]
_SPINNER_COLORS = ["#4285F4", "#6366F1", "#8B5CF6", "#A855F7", "#C026D3", "#A855F7", "#8B5CF6", "#6366F1"]

# Per-letter gradient for the static header
_GEMINI_GRAD = ["#4285F4", "#6366F1", "#8B5CF6", "#A855F7", "#C026D3", "#EC4899"]

def _gemini_header() -> str:
    parts = [f"[bold {c}]{ch}[/bold {c}]" for c, ch in zip(_GEMINI_GRAD, "GEMINI")]
    return f"[bold #4285F4]✦[/bold #4285F4] {''.join(parts)}"

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
        padding: 0 2;
        height: auto;
        border-bottom: solid $surface;
    }
    #dp-meta {
        padding: 0 2;
        height: auto;
        border-bottom: solid $surface;
    }
    #dp-actions {
        padding: 0 2;
        height: 4;
        border-bottom: solid $surface;
        align: left middle;
    }
    #dp-actions Button {
        margin-right: 1;
        min-width: 16;
        padding: 0;
        text-align: center;
    }
    #btn-detail-update {
        background: #3B82F6;
        border: round #3B82F6;
    }
    #btn-detail-update:hover {
        background: #2563EB;
        border: round #2563EB;
    }
    #btn-detail-remove {
        background: #DC2626;
        border: round #DC2626;
    }
    #btn-detail-remove:hover {
        background: #B91C1C;
        border: round #B91C1C;
    }
    #dp-ai-scroll {
        height: 1fr;
    }
    #dp-graph {
        padding: 1 2;
        height: auto;
        border-bottom: solid $surface;
    }
    #dp-cve {
        padding: 0 2;
        height: auto;
        border-bottom: solid $surface;
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
            yield Button("↑\nupdate", id="btn-detail-update", variant="primary")
            yield Button("✕\nremove", id="btn-detail-remove", variant="error")
        with VerticalScroll(id="dp-ai-scroll"):
            yield Static("", id="dp-graph")
            yield Static("", id="dp-cve")
            yield Static("", id="dp-ai")

    def on_mount(self) -> None:
        self.show_empty()

    def show_empty(self, msg: str = "Select a package to see details.") -> None:
        self.query_one("#dp-header", Static).update(f"[dim]{msg}[/dim]")
        self.query_one("#dp-meta", Static).update("")
        self.query_one("#dp-graph", Static).update("")
        self.query_one("#dp-cve", Static).update("")
        self.query_one("#dp-ai", Static).update("")
        self.query_one("#dp-actions").display = False

    def show_graph(self, content: str) -> None:
        self.query_one("#dp-graph", Static).update(content)

    def show_cve(self, content: str) -> None:
        self.query_one("#dp-cve", Static).update(content)

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
        meta = (
            f"[dim]manager[/dim]  [{color}]{pkg.manager}[/{color}]  "
            f"[dim]version[/dim]  {pkg.version}"
        )
        if pkg.install_date:
            meta += f"  [dim]installed[/dim]  {pkg.install_date}"
        if pkg.source:
            meta += f"\n[dim]source[/dim]  [dim]{pkg.source}[/dim]"
        self.query_one("#dp-meta", Static).update(meta)
        self.query_one("#dp-cve", Static).update(
            "[dim]s[/dim] [dim]→ scan for CVEs[/dim]"
        )

        header = _gemini_header()
        if ai_text:
            ai_block = f"{header}\n\n{ai_text}"
        elif ai_loading:
            ai_block = f"{header}\n\n[dim]Loading…[/dim]"
        else:
            ai_block = f"{header}\n\n[dim]Press 'a' for AI insights[/dim]"

        self.query_one("#dp-ai", Static).update(ai_block)
        self.query_one("#dp-actions").display = True


# ---------------------------------------------------------------------------
# Delete confirmation modal
# ---------------------------------------------------------------------------

class ConfirmDeleteModal(ModalScreen[bool]):
    DEFAULT_CSS = """
    ConfirmDeleteModal { align: center middle; }
    #modal-box {
        width: 58; height: auto; max-height: 80%;
        border: thick $error; background: $surface; padding: 1 2;
    }
    #modal-title { text-align: center; color: $error; text-style: bold; margin-bottom: 1; }
    #modal-pkg   { text-align: center; margin-bottom: 1; }
    #modal-hint  { text-align: center; margin-bottom: 1; }
    #modal-output { background: $panel; padding: 1; margin-bottom: 1; height: auto; max-height: 10; }
    #modal-buttons { layout: horizontal; align: center middle; height: 3; }
    #modal-buttons Button { margin: 0 2; }
    """

    def __init__(self, pkg: Package, dry_run_output: str = "") -> None:
        super().__init__()
        self.pkg = pkg
        self.dry_run_output = dry_run_output

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-box"):
            yield Label("Delete Package (Preview)", id="modal-title")
            yield Label(
                f"[white]{self.pkg.name}[/white]  "
                f"[dim]{self.pkg.manager} {self.pkg.version}[/dim]",
                id="modal-pkg",
            )
            yield Label("[dim]This action cannot be undone.[/dim]", id="modal-hint")
            if self.dry_run_output:
                with VerticalScroll(id="modal-output"):
                    yield Static(self.dry_run_output)
            with Horizontal(id="modal-buttons"):
                yield Button("Cancel", variant="default", id="btn-cancel")
                yield Button("Delete", variant="error", id="btn-confirm")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "btn-confirm")


class ConfirmUpdateModal(ModalScreen[bool]):
    DEFAULT_CSS = """
    ConfirmUpdateModal { align: center middle; }
    #modal-box {
        width: 58; height: auto; max-height: 80%;
        border: thick $primary; background: $surface; padding: 1 2;
    }
    #modal-title { text-align: center; color: $primary; text-style: bold; margin-bottom: 1; }
    #modal-pkg   { text-align: center; margin-bottom: 1; }
    #modal-output { background: $panel; padding: 1; margin-bottom: 1; height: auto; max-height: 10; }
    #modal-buttons { layout: horizontal; align: center middle; height: 3; }
    #modal-buttons Button { margin: 0 2; }
    """

    def __init__(self, pkg: Package, dry_run_output: str = "") -> None:
        super().__init__()
        self.pkg = pkg
        self.dry_run_output = dry_run_output

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-box"):
            yield Label("Update Package (Preview)", id="modal-title")
            yield Label(
                f"[white]{self.pkg.name}[/white]  "
                f"[dim]{self.pkg.manager} {self.pkg.version}[/dim]",
                id="modal-pkg",
            )
            if self.dry_run_output:
                with VerticalScroll(id="modal-output"):
                    yield Static(self.dry_run_output)
            with Horizontal(id="modal-buttons"):
                yield Button("Cancel", variant="default", id="btn-cancel")
                yield Button("Update", variant="primary", id="btn-confirm")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "btn-confirm")


# ---------------------------------------------------------------------------
# Dependency graph modal
# ---------------------------------------------------------------------------

class GraphModal(ModalScreen[None]):
    DEFAULT_CSS = """
    GraphModal { align: center middle; }
    #graph-box {
        width: 90%; height: 80%;
        border: thick $primary; background: $surface; padding: 1 2;
    }
    #graph-title { text-align: center; text-style: bold; margin-bottom: 1; }
    #graph-scroll { height: 1fr; }
    #graph-content { height: auto; }
    #graph-hint { text-align: center; color: $text-muted; margin-top: 1; }
    """

    BINDINGS = [Binding("escape,g,q", "dismiss", show=False)]

    def __init__(self, pkg_name: str, ascii_art: str) -> None:
        super().__init__()
        self._pkg_name = pkg_name
        self._ascii_art = ascii_art

    def compose(self) -> ComposeResult:
        with Vertical(id="graph-box"):
            yield Label(f"Dependencies — {self._pkg_name}", id="graph-title")
            with VerticalScroll(id="graph-scroll"):
                yield Static(self._ascii_art, id="graph-content")
            yield Label("[dim]esc / g to close[/dim]", id="graph-hint")

    async def action_dismiss(self, result: Any | None = None) -> None:
        self.dismiss(result)


# ---------------------------------------------------------------------------
# Smart cleanup — loading modal
# ---------------------------------------------------------------------------

class CleanupLoadingModal(ModalScreen[None]):
    DEFAULT_CSS = """
    CleanupLoadingModal { align: center middle; }
    #cl-box {
        width: 54; height: auto;
        border: thick $primary; background: $surface; padding: 2 4;
    }
    #cl-text { text-align: center; }
    """

    BINDINGS = [Binding("escape", "dismiss", show=False)]

    def __init__(self, total: int) -> None:
        super().__init__()
        self._total = total
        self._frame = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="cl-box"):
            yield Static("", id="cl-text")

    def on_mount(self) -> None:
        self._tick()
        self.set_interval(0.2, self._tick)

    def _tick(self) -> None:
        idx = self._frame % len(_SPINNER_CHARS)
        char = _SPINNER_CHARS[idx]
        color = _SPINNER_COLORS[idx]
        self._frame += 1
        try:
            self.query_one("#cl-text", Static).update(
                f"{_gemini_header()}\n\n"
                f"[bold {color}]{char}[/bold {color}] "
                f"[dim]Analyzing {self._total} packages…[/dim]"
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Smart cleanup modal
# ---------------------------------------------------------------------------

class CleanupModal(ModalScreen[dict[str, Any] | None]):
    DEFAULT_CSS = """
    CleanupModal { align: center middle; }
    #cleanup-box {
        width: 90%; height: 80%;
        border: thick $primary; background: $surface; padding: 1 2;
    }
    #cleanup-title   { text-align: center; text-style: bold; margin-bottom: 1; }
    #cleanup-summary { height: auto; margin-bottom: 1; }
    #cleanup-table   { height: 1fr; }
    #cleanup-hint    { text-align: center; color: $text-muted; margin-top: 1; }
    """

    BINDINGS = [
        Binding("d,enter", "select_package", show=False),
        Binding("escape,c", "dismiss_modal", show=False),
    ]

    def __init__(self, recommendations: list[dict[str, Any]], total_scanned: int) -> None:
        super().__init__()
        self._recs = recommendations
        self._total = total_scanned

    def compose(self) -> ComposeResult:
        remove_count = sum(1 for r in self._recs if r.get("verdict") == "remove")
        review_count = sum(1 for r in self._recs if r.get("verdict") == "review")
        with Vertical(id="cleanup-box"):
            yield Label(f"{_gemini_header()}  Smart Cleanup", id="cleanup-title")
            if not self._recs:
                yield Static(
                    f"[dim]Analyzed {self._total} packages[/dim]\n\n"
                    "[bold green]✓ Everything looks healthy — no cleanup needed.[/bold green]",
                    id="cleanup-summary",
                )
                yield Label("[dim]esc to close[/dim]", id="cleanup-hint")
            else:
                yield Static(
                    f"[dim]Analyzed {self._total} packages  ·  "
                    f"[red]{remove_count} flagged for removal[/red]  ·  "
                    f"[yellow]{review_count} to review[/yellow][/dim]",
                    id="cleanup-summary",
                )
                yield DataTable(id="cleanup-table", cursor_type="row", zebra_stripes=True)
                yield Label(
                    "[dim]↑↓ navigate   d / enter to delete selected   esc to close[/dim]",
                    id="cleanup-hint",
                )

    def on_mount(self) -> None:
        if not self._recs:
            return
        table = self.query_one("#cleanup-table", DataTable)
        table.add_columns("VERDICT", "PACKAGE", "MANAGER", "REASON")
        for i, rec in enumerate(self._recs):
            verdict = rec.get("verdict", "review")
            verdict_markup = "[red]● remove[/red]" if verdict == "remove" else "[yellow]⚠ review[/yellow]"
            color = _mgr_color(rec.get("manager", ""))
            table.add_row(
                verdict_markup,
                f"[bold]{rec.get('name', '')}[/bold]",
                f"[{color}]{rec.get('manager', '')}[/{color}]",
                f"[dim]{rec.get('reason', '')}[/dim]",
                key=str(i),
            )

    def action_select_package(self) -> None:
        if not self._recs:
            return
        try:
            row = self.query_one("#cleanup-table", DataTable).cursor_row
            if 0 <= row < len(self._recs):
                self.dismiss(self._recs[row])
                return
        except Exception:
            pass
        self.dismiss(None)

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

class XYZApp(App[None]):
    TITLE = "xyz — dependency manager"

    BINDINGS = [
        Binding("u",      "update_package", "u update",      show=False),
        Binding("d",      "delete_package", "d delete",      show=False),
        Binding("U",      "upgrade_all",    "U upgrade all", show=False),
        Binding("o",      "toggle_orphans", "o orphans",     show=False),
        Binding("m",      "cycle_manager",  "m manager",     show=False),
        Binding("a",      "ask_ai",         "a AI",          show=False),
        Binding("s",      "scan_cve",       "s CVE scan",    show=False),
        Binding("g",      "view_graph",     "g graph",       show=False),
        Binding("c",      "smart_cleanup",  "c cleanup",     show=False),
        Binding("/",      "focus_search",   "/ search",      show=False),
        Binding("escape", "blur_search",    "esc back",      show=False),
        Binding("ctrl+q", "quit",           "ctrl+q quit",   show=False),
    ]

    DEFAULT_CSS = """
    Screen { layout: vertical; }

    /* ── search bar ── */
    #search-row {
        height: 3;
        padding: 0 1;
        background: $panel;
        border-bottom: solid $primary-darken-2;
        align: left middle;
    }
    #search-label {
        width: auto;
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
        height: 3;
        align: left middle;
    }
    .manager-pill {
        height: 3;
        min-width: 7;
        border: none;
        margin: 0 0 0 1;
        color: white;
    }
    /* per-manager pill colours */
    #pill-pip    { background: #3B82F6; border: round #3B82F6; }
    #pill-npm    { background: #22C55E; border: round #22C55E; }
    #pill-brew   { background: #EF4444; border: round #EF4444; }
    #pill-apt    { background: #EAB308; border: round #EAB308; color: black; }
    #pill-bun    { background: #F97316; border: round #F97316; }
    #pill-pacman { background: #A855F7; border: round #A855F7; }

    /* active pill — white border only */
    #pill-pip.pill-active    { border: round white; }
    #pill-npm.pill-active    { border: round white; }
    #pill-brew.pill-active   { border: round white; }
    #pill-apt.pill-active    { border: round white; }
    #pill-bun.pill-active    { border: round white; }
    #pill-pacman.pill-active { border: round white; }

    /* pill hover — darken each colour */
    #pill-pip:hover    { background: #2563EB; border: round #2563EB; }
    #pill-npm:hover    { background: #16A34A; border: round #16A34A; }
    #pill-brew:hover   { background: #DC2626; border: round #DC2626; }
    #pill-apt:hover    { background: #CA8A04; border: round #CA8A04; }
    #pill-bun:hover    { background: #EA580C; border: round #EA580C; }
    #pill-pacman:hover { background: #9333EA; border: round #9333EA; }

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
        self._display_rows: Sequence[Package | None] = []
        self._dupe_names: set[str] = set()
        self._selected: Optional[Package] = None
        self._orphan_only: bool = False
        self._manager_filter: Optional[str] = None
        self._managers: list[str] = []
        self._ai_task: Optional[asyncio.Task[None]] = None
        self._spinner_timer: Any = None
        self._spinner_frame: int = 0
        self._graph_task: Optional[asyncio.Task[None]] = None
        self._current_graph_ascii: str = ""
        self._cve_task: Optional[asyncio.Task[None]] = None

    def compose(self) -> ComposeResult:
        with Horizontal(id="search-row"):
            yield Label("search", id="search-label")
            yield Input(placeholder="Try using '?AI' to search for all AI related packages", id="search-input")
            yield Label("", id="result-count")
            yield Horizontal(id="manager-pills")
        with Horizontal(id="main-row"):
            yield DataTable(id="package-list", cursor_type="row", zebra_stripes=True)
            yield DetailPane(id="detail-pane")
        yield Static("", id="stats-bar")
        yield Static(
            "↑↓ navigate   u update   d delete   a AI   s CVE scan   g graph   o orphans   c cleanup   / search   ctrl+q quit",
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

    async def _reload_packages(self) -> None:
        """Re-scan all package managers and refresh the UI in the background."""
        self.notify("Refreshing package list…", title="Refresh", timeout=2)
        packages = await self._managers_registry.scan_all()
        self._all_packages = packages
        new_managers = sorted({p.manager for p in packages})
        name_counts = Counter(p.name for p in packages)
        self._dupe_names = {n for n, c in name_counts.items() if c > 1}

        container = self.query_one("#manager-pills")
        for manager in new_managers:
            if manager not in self._managers:
                container.mount(Button(manager, id=f"pill-{manager}", classes="manager-pill"))
        self._managers = new_managers

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
        if self._graph_task and not self._graph_task.done():
            self._graph_task.cancel()
        if self._cve_task and not self._cve_task.done():
            self._cve_task.cancel()
        self.query_one(DetailPane).show_package(pkg, self._dupe_names)
        self._graph_task = asyncio.create_task(self._fetch_graph(pkg))

    def _kick_ai(self, pkg: Package) -> None:
        if self._ai_task and not self._ai_task.done():
            self._ai_task.cancel()
        self._ai_task = asyncio.create_task(self._fetch_ai(pkg))

    def _start_ai_spinner(self) -> None:
        self._spinner_frame = 0
        if self._spinner_timer is not None:
            self._spinner_timer.stop()
        self._tick_spinner()
        self._spinner_timer = self.set_interval(0.2, self._tick_spinner)

    def _tick_spinner(self) -> None:
        idx = self._spinner_frame % len(_SPINNER_CHARS)
        char = _SPINNER_CHARS[idx]
        color = _SPINNER_COLORS[idx]
        self._spinner_frame += 1
        try:
            self.query_one("#dp-ai", Static).update(
                f"{_gemini_header()}\n\n[bold {color}]{char}[/bold {color}] [dim]Asking Gemini…[/dim]"
            )
        except Exception:
            pass

    def _stop_ai_spinner(self) -> None:
        if self._spinner_timer is not None:
            self._spinner_timer.stop()
            self._spinner_timer = None

    async def _fetch_ai(self, pkg: Package) -> None:
        try:
            accumulated = ""
            spinner_stopped = False
            stream = (
                stream_assess_orphan_risk(pkg.name, pkg.manager)
                if pkg.is_orphan
                else stream_explain_package(pkg.name, pkg.manager, pkg.version)
            )
            async for chunk in stream:
                if self._selected and self._selected.name != pkg.name:
                    return
                if not spinner_stopped:
                    self._stop_ai_spinner()
                    spinner_stopped = True
                accumulated += chunk
                try:
                    self.query_one("#dp-ai", Static).update(
                        f"{_gemini_header()}\n\n{accumulated}"
                    )
                except Exception:
                    pass
        except asyncio.CancelledError:
            self._stop_ai_spinner()
        except Exception as exc:
            self._stop_ai_spinner()
            if self._selected and self._selected.name == pkg.name:
                self.query_one(DetailPane).show_package(
                    pkg, self._dupe_names, ai_text=f"[red]Error: {exc}[/red]"
                )

    async def _fetch_graph(self, pkg: Package) -> None:
        detail = self.query_one(DetailPane)
        self._current_graph_ascii = ""
        detail.show_graph("[dim]Loading dependencies…[/dim]")
        try:
            manager = self._managers_registry.get_manager(pkg.manager)
            if manager is None:
                detail.show_graph("")
                return
            requires, required_by = await manager.get_deps(pkg.name)
            if self._selected and self._selected.name != pkg.name:
                return
            if not requires and not required_by:
                detail.show_graph("[dim]No dependency data available.[/dim]")
                return
            mermaid_str = _build_mermaid(pkg.name, requires, required_by)
            ascii_art = await _render_graph(mermaid_str)
            if self._selected and self._selected.name != pkg.name:
                return
            if ascii_art:
                self._current_graph_ascii = ascii_art
                n_req = len(requires)
                n_rev = len(required_by)
                detail.show_graph(
                    f"[bold]DEPENDENCIES[/bold]  "
                    f"[dim]{n_req} requires · {n_rev} required by[/dim]  "
                    f"[dim]press G to view[/dim]"
                )
            else:
                detail.show_graph("[dim]Graph rendering unavailable.[/dim]")
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            if self._selected and self._selected.name == pkg.name:
                detail.show_graph(f"[dim]Graph error: {exc}[/dim]")

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
        self._start_ai_spinner()

        try:
            package_names = [p.name for p in self._all_packages]
            matches = await natural_language_search(query[1:].strip(), package_names)
            matched_pkgs = [p for p in self._all_packages if p.name in matches]
            self._display_rows = matched_pkgs
            self._rebuild_table()
            self.query_one("#result-count", Label).update(f"{len(matched_pkgs)} results")
            if not matched_pkgs:
                self.query_one(DetailPane).show_empty("No AI matches found.")
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            self.query_one(DetailPane).show_empty(f"AI search error: {exc}")
        finally:
            self._stop_ai_spinner()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id.startswith("pill-"):
            self._toggle_pill(btn_id[5:])
            event.stop()
        elif btn_id == "btn-detail-update":
            self.action_update_package()
            event.stop()
        elif btn_id == "btn-detail-remove":
            self.action_delete_package()
            event.stop()

    # ── actions ──────────────────────────────────────────────────────────────

    def action_focus_search(self) -> None:
        self.query_one("#search-input", Input).focus()

    def action_blur_search(self) -> None:
        self.query_one("#package-list", DataTable).focus()

    def action_view_graph(self) -> None:
        if not self._current_graph_ascii:
            self.notify("No graph available — select a package first.", severity="warning")
            return
        name = self._selected.name if self._selected else "Package"
        self.push_screen(GraphModal(name, self._current_graph_ascii))

    def action_ask_ai(self) -> None:
        if not self._selected:
            self.notify("No package selected.", severity="warning")
            return
        self.query_one(DetailPane).show_package(self._selected, self._dupe_names, ai_loading=True)
        self._start_ai_spinner()
        self._kick_ai(self._selected)

    def action_scan_cve(self) -> None:
        if not self._selected:
            self.notify("No package selected.", severity="warning")
            return
        pkg = self._selected
        if self._cve_task and not self._cve_task.done():
            self._cve_task.cancel()
        self.query_one(DetailPane).show_cve(
            f"{_gemini_header()}  [dim]Scanning for CVEs…[/dim]"
        )
        self._cve_task = asyncio.create_task(self._fetch_cve(pkg))

    async def _fetch_cve(self, pkg: Package) -> None:
        try:
            result = await check_package_cves(pkg.name, pkg.manager, pkg.version)
        except asyncio.CancelledError:
            return
        except Exception as exc:
            if self._selected and self._selected.name == pkg.name:
                self.query_one(DetailPane).show_cve(f"[red]CVE scan error: {exc}[/red]")
            return

        if self._selected and self._selected.name != pkg.name:
            return

        severity = result.get("severity", "unknown")
        cve_ids = result.get("cve_ids", [])
        summary = result.get("summary", "")

        severity_markup = {
            "none":     "[bold green]✓ No known CVEs[/bold green]",
            "low":      "[bold yellow]⚠ Low severity[/bold yellow]",
            "medium":   "[bold yellow]⚠ Medium severity[/bold yellow]",
            "high":     "[bold red]✘ High severity[/bold red]",
            "critical": "[bold red]✘ CRITICAL[/bold red]",
        }.get(severity, "[dim]Unknown[/dim]")

        header = f"{_gemini_header()}  {severity_markup}"
        cve_line = "  ".join(f"[dim]{c}[/dim]" for c in cve_ids) if cve_ids else ""
        body = f"\n{cve_line}" if cve_line else ""
        body += f"\n[dim]{summary}[/dim]" if summary else ""

        try:
            self.query_one(DetailPane).show_cve(header + body)
        except Exception:
            pass

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

    @work
    async def action_update_package(self) -> None:
        if not self._selected:
            self.notify("No package selected.", severity="warning")
            return
        pkg = self._selected
        
        self.notify(f"Fetching update preview for [bold]{pkg.name}[/bold]…", title="Preview")
        preview_success, preview_output = await self._managers_registry.update(pkg, dry_run=True)
        if not preview_output:
            preview_output = "Dry run preview unavailable or empty."

        confirmed: bool = await self.push_screen_wait(ConfirmUpdateModal(pkg, preview_output))
        if confirmed:
            self.notify(f"Updating [bold]{pkg.name}[/bold]…", title="Update")
            success, output = await self._managers_registry.update(pkg)
            if success:
                self.notify(f"Successfully updated {pkg.name}\n[dim]{output}[/dim]", title="Update Success")
                self.run_worker(self._reload_packages())
            else:
                self.notify(f"Failed to update {pkg.name}\n{output}", title="Update Error", severity="error")

    @work
    async def action_delete_package(self) -> None:
        if not self._selected:
            self.notify("No package selected.", severity="warning")
            return
        pkg = self._selected

        self.notify(f"Fetching delete preview for [bold]{pkg.name}[/bold]…", title="Preview")
        preview_success, preview_output = await self._managers_registry.delete(pkg, dry_run=True)
        if not preview_output:
            preview_output = "Dry run preview unavailable or empty."

        confirmed: bool = await self.push_screen_wait(ConfirmDeleteModal(pkg, preview_output))
        if confirmed:
            self.notify(f"Deleting [bold]{pkg.name}[/bold]…", title="Delete", severity="warning")
            success, output = await self._managers_registry.delete(pkg)
            if success:
                self.notify(f"Successfully deleted {pkg.name}\n[dim]{output}[/dim]", title="Delete Success")
                self._all_packages = [p for p in self._all_packages if not (p.name == pkg.name and p.manager == pkg.manager)]
                self._apply_filters()
                self.run_worker(self._reload_packages())
            else:
                self.notify(f"Failed to delete {pkg.name}\n{output}", title="Delete Error", severity="error")

    @work
    async def action_smart_cleanup(self) -> None:
        if not self._all_packages:
            self.notify("No packages loaded yet.", severity="warning")
            return
        loading = CleanupLoadingModal(len(self._all_packages))
        self.push_screen(loading)
        try:
            pkg_dicts = [
                {"name": p.name, "manager": p.manager, "version": p.version}
                for p in self._all_packages
            ]
            recs = await smart_cleanup(pkg_dicts, dupe_names=self._dupe_names)
        except Exception as exc:
            try:
                loading.dismiss()
            except Exception:
                pass
            self.notify(f"Cleanup analysis failed: {exc}", severity="error")
            return

        try:
            loading.dismiss()
        except Exception:
            pass

        result: Optional[dict[str, Any]] = await self.push_screen_wait(CleanupModal(recs, len(self._all_packages)))
        if result is None:
            return

        pkg = next(
            (p for p in self._all_packages if p.name == result["name"] and p.manager == result["manager"]),
            None,
        )
        if pkg is None:
            self.notify("Package not found in list.", severity="warning")
            return

        confirmed: bool = await self.push_screen_wait(ConfirmDeleteModal(pkg))
        if confirmed:
            self.notify(f"Deleting [bold]{pkg.name}[/bold]…", title="Delete", severity="warning")
            success, output = await self._managers_registry.delete(pkg)
            if success:
                self.notify(f"Successfully deleted {pkg.name}", title="Delete Success")
                self._all_packages = [
                    p for p in self._all_packages
                    if not (p.name == pkg.name and p.manager == pkg.manager)
                ]
                self._apply_filters()
                self.run_worker(self._reload_packages())
            else:
                self.notify(f"Failed to delete {pkg.name}\n{output}", title="Delete Error", severity="error")

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
