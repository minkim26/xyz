# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

XYZ is a terminal-based universal dependency manager TUI (BeaverHacks hackathon MVP). It aggregates packages from pip, npm, and brew into one interactive interface with fuzzy search, update/delete actions, orphan detection, dependency graphs, CVE scanning, and an AI explainer powered by Google Gemini.

## Commands

**Install for development:**
```bash
pip install -e ".[dev]"
```

**Run:**
```bash
xyz
GEMINI_API_KEY=your_key xyz   # with AI features
```

**Tests:**
```bash
pytest
pytest tests/managers/test_pip.py::test_list_parses_packages  # single test
pytest --cov=src --cov-report=term-missing                    # with coverage
```

**Type check / lint:**
```bash
mypy src/
ruff check src/
ruff format src/
```

## Architecture

Three layers with strict one-way dependency: `managers` → `ai` ← `tui` (the TUI imports from both; managers never import from TUI or AI).

### 1. Package Manager Layer (`src/xyz/managers/`)

- `Package` — frozen dataclass: `name`, `version`, `manager`, `size` (bytes, nullable), `is_orphan`, `install_date`, `source`
- `BaseManager` — abstract base; concrete subclasses: `PipManager`, `NpmManager`, `BrewManager`
- `ManagerRegistry` — detects available managers via `shutil.which`, runs `asyncio.gather` over all `list()` and `check_orphans()` calls with a 3-second per-manager timeout; failed managers log a warning and are skipped
- `_subprocess.run_command` — all CLI calls go through this async wrapper; tests patch it via the `fake_subprocess` fixture in `conftest.py`

### 2. TUI Layer (`src/xyz/tui/app.py`)

Built with Textual. The entire app is a single `App` subclass.

- Two-panel layout: `DataTable` (left) + detail pane (right)
- Keybindings: `j`/`k` navigate, `U` update, `D` delete (dry-run modal first), `Shift+U` upgrade all, `O` toggle orphan filter
- `?`-prefixed search triggers natural language search via AI; plain search is synchronous fuzzy filter
- Dependency graphs rendered with `mermaid-ascii` via `_build_mermaid` / `_render_graph` helpers
- AI calls use `@work` decorator (Textual background workers) — the TUI never `await`s AI directly

### 3. AI Layer (`src/xyz/ai/`)

- `GeminiClient` — singleton (`GeminiClient.get_instance()`); uses `gemini-2.5-flash-lite` for most calls, `gemini-2.5-flash` for CVE/search-grounded calls; enforces a local 14 req/min rate limit
- `explainer.py` — `stream_explain_package` / `explain_package`; in-memory cache keyed on `(name, manager)` to avoid duplicate API calls
- `orphan.py` — `stream_assess_orphan_risk` / `assess_orphan_risk`
- `search.py` — `natural_language_search`; maps free-text to installed package names
- `cleanup.py` — `smart_cleanup`; batch analysis returning `remove`/`review` verdicts
- `cve.py` — `check_package_cves`; uses search grounding to find real CVE IDs
- `prompts.py` — all prompt templates
- `__init__.py` — public wrappers that inject the singleton client; TUI calls these directly

## Key Constraints

- **Never block the TUI on subprocess or API calls.** Manager scans use `asyncio.gather`; AI calls use Textual `@work` workers.
- **All destructive package actions require a dry-run preview and explicit confirmation.** No silent deletes.
- **The manager layer must not import from the TUI or AI layers.**
- Startup goal: full package list within 3 seconds on a 500+ package machine.
- Search goal: results within 50ms per keystroke.
- `asyncio_mode = "auto"` is set in `pyproject.toml` — no `@pytest.mark.asyncio` decorator needed on async tests.

## Environment

- `GEMINI_API_KEY` — required only for AI features; app runs fully offline without it
- Python 3.10+ required (uses `match` statements and modern `asyncio` patterns)
- Use the `gemini-api-docs-mcp` MCP server (enabled in `.claude/settings.local.json`) when writing or debugging Gemini API code
