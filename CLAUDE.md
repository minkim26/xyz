# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

XYZ is a terminal-based universal dependency manager TUI (BeaverHacks hackathon MVP). It aggregates packages from multiple package managers into one interactive interface with fuzzy search, update/delete actions, orphan detection, and an AI explainer powered by Google Gemini.

**Install for development:**
```bash
pip install -e .
```

**Run:**
```bash
xyz
# or with AI features
GEMINI_API_KEY=your_key xyz
```

**Tests** (once written):
```bash
pytest
pytest tests/test_managers.py::TestPipManager  # single test
```

**Type check / lint** (once configured):
```bash
mypy src/
ruff check src/
```

## Architecture

The codebase is split into three layers that must stay independent:

### 1. Package Manager Abstraction Layer (`src/xyz/managers/`)

- `Package` — dataclass with fields: `name`, `version`, `manager`, `size`, `is_orphan`
- `BaseManager` — abstract base with async methods: `list()`, `update(name)`, `delete(name)`, `check_orphans()`
- One concrete class per manager: `PipManager`, `NpmManager`, `BrewManager`, `AptManager`, `PacmanManager`, `BunManager`
- `ManagerRegistry` — collects all available managers, runs `asyncio.gather` over all `list()` calls on startup, applies per-manager timeouts so a slow or absent manager never blocks the UI
- Parsers call the manager CLI via `subprocess` and parse stdout; the manager CLI is the source of truth, not any lock file

### 2. TUI Layer (`src/xyz/tui/`)

Built with [Textual](https://github.com/Textualize/textual). Consumes the `Package` dataclass payload from `ManagerRegistry` without knowing which manager produced it.

- Two-panel layout: package list (left) + detail pane (right)
- `DataTable` with columns: name, manager, version, size
- Incremental fuzzy search bar — filters `DataTable` in real time
- Keybindings: `j`/`k` or arrow keys to navigate, `U` update, `D` delete (with dry-run modal + confirmation), `Shift+U` upgrade all, `O` toggle orphan filter
- Orphan filter narrows list to packages where `is_orphan=True`
- All destructive actions show a dry-run preview modal before executing

### 3. AI Layer (`src/xyz/ai/`)

- `explain_package(name, manager, version)` — async function; calls Gemini API, returns plain-English: what the package does, why it is likely installed, whether it is safe to remove
- `assess_orphan_risk(name, manager)` — called automatically when an orphaned package is selected
- Natural language search — triggered by `?` prefix in the search bar; Gemini maps free-text intent to matching package names
- All Gemini calls run as background async workers; the TUI never awaits them synchronously
- Graceful fallback: if `GEMINI_API_KEY` is not set, the detail pane shows an offline message and all non-AI features remain available
- Use the `gemini-api-docs-mcp` MCP server (enabled in `.claude/settings.local.json`) when writing or debugging Gemini API code

## Key Constraints

- **Never block the TUI on subprocess or API calls.** Manager scans use `asyncio.gather`; Gemini calls are background workers.
- **All destructive package actions require a dry-run preview and explicit confirmation.** No silent deletes.
- **Never cache or store sudo credentials.** Prompt inline when a manager requires elevated privileges.
- **The manager layer must not import from the TUI layer.** The TUI consumes `Package` objects; the manager layer produces them. Dependency direction is one-way.
- Startup goal: full package list within 3 seconds on a 500+ package machine.
- Search goal: results within 50ms per keystroke.

## Environment

- `GEMINI_API_KEY` — required only for AI features; app runs fully offline without it
- Python 3.10+ required (uses `match` statements and modern `asyncio` patterns)
