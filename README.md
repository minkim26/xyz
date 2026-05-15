# XYZ — Universal Dependency Manager

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/xyz-logo-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/xyz-logo-light.svg">
  <img alt="Project Logo" src="assets/xyz-logo-dark.svg">
</picture>

> One terminal. Every package manager. No more context switching.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![TUI](https://img.shields.io/badge/TUI-Textual-6e40c9?logo=python&logoColor=white)](https://textual.textualize.io/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/xyz-manager?color=blue)](https://pypi.org/project/xyz-manager/)
[![CI](https://img.shields.io/github/actions/workflow/status/xyz-tui/xyz/ci.yml?branch=main)](https://github.com/xyz-tui/xyz/actions)

[Quick Start](#getting-started) · [Features](#features) · [Keybindings](#keybindings) · [Development](#development-setup) · [Contributing](CONTRIBUTING.md)

---

## What is XYZ?

XYZ is a terminal-based dependency manager that gives you a single interactive interface across your package managers. Instead of juggling `pip list`, `brew info`, and `npm ls` in separate sessions, XYZ aggregates everything into one searchable, actionable TUI — powered by AI.

Select an unfamiliar package and XYZ will tell you exactly what it is, why it's probably on your machine, and whether it's safe to remove. No browser. No tab switching. No guessing.

---

## Features

### Highlights

- **Unified package list** — aggregates installed packages from detected managers into one view
- **Live search + manager filtering** — substring filtering, manager pills, and orphan-only toggle
- **Natural language AI search** — prefix search with `?` (e.g., `?AI` or `?database`) to find packages by intent using Gemini
- **Safe package actions** — update/delete with dry-run preview modal before confirmation
- **Auto-refresh after actions** — package list re-scans after updates/deletes

### Intelligence

- **Orphan detection (non-AI)** — manager-native orphan checks for `pip`, `npm`, and `brew`
- **AI package explainer (streaming)** — streamed Gemini explanations in the detail pane
- **Smart cleanup recommendations** — Gemini-powered remove/review suggestions
- **Dependency graph view** — dependency graph preview + fullscreen modal (when `mermaid-ascii` is available)
- **CVE scan** — Gemini Search-grounded vulnerability summary for selected package

---

## Keybindings

| Key | Action |
|-----|--------|
| `↑/↓` | Navigate package list |
| `u` | Update selected package |
| `d` | Delete selected package |
| `U` | Upgrade all outdated packages |
| `a` | Fetch AI explanation |
| `s` | Scan selected package for CVEs |
| `g` | View dependency graph |
| `o` | Toggle orphan packages filter |
| `m` | Cycle manager filter |
| `c` | Run smart cleanup analysis |
| `/` | Focus search bar (prefix with `?` for AI search) |
| `esc` | Blur search or close modals |
| `ctrl+q` | Quit |

---

## Supported Package Managers

| Manager | Platform |
|---------|----------|
| `pip` | Python (all platforms) |
| `brew` | macOS / Linux |
| `npm` | Node.js (all platforms) |

Current release auto-detects and integrates: `pip`, `brew`, and `npm`.

---

## Getting Started

### Requirements

- Python 3.10+
- One or more of the supported package managers installed

### Install (Users)

XYZ inspects the packages available to your current Python environment. For most users, that means installing into your system or user site (not a virtual environment) so XYZ can see the same packages you want to clean up.

```bash
pip install --user xyz-manager
```

### Run

```bash
xyz
# or
python -m xyz
```

### Gemini API Key (for AI explainer)

```bash
export GEMINI_API_KEY=your_key_here
xyz
```

Without a key, XYZ runs in offline mode: package listing/search/filtering and package actions remain available; AI features (AI search, explainer, smart cleanup, CVE scan) are disabled.

---

## Development Setup

### Clone and install

#### Create an isolated environment

For development, use a virtual environment so you do not pollute your system Python.

**Option 1: venv**

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

**Option 2: uv**

```bash
uv venv .venv
source .venv/bin/activate
```

```bash
git clone https://github.com/xyz-tui/xyz.git
cd xyz
pip install -e ".[dev]"
```

### Run locally

```bash
xyz
# or
python -m xyz
```

### Run tests

```bash
pytest
ruff check src/ tests/
mypy src/
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.10+ |
| TUI Framework | [Textual](https://textual.textualize.io/) |
| AI Integration | [Google Gemini API](https://ai.google.dev/) |
| Package parsing | Native subprocess calls per manager |
| Distribution | pip / PyPI |

---

## Roadmap

- [ ] **v1.1** — Snapshot & restore (export full package state to `packages.toml`, restore on new machine)
- [ ] **v1.2** — CVE security overlay via OSV API
- [ ] **v1.3** — Duplicate detection (same package across multiple managers)
- [ ] **v1.4** — Audit trail with install-reason annotations
- [ ] **Post-MVP** — expand manager coverage (`apt`, `pacman`, `bun`, `cargo`, `conda`, `pipx`, `gem`, `winget`)

---

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for our development workflow and coding standards.

---

## License

MIT. See [LICENSE](LICENSE) for the full text.

---

## Team

| Name | Role |
|------|------|
| [Minsu Kim](https://github.com/minkim26) | Maintainer |
| [Adithya Nair](https://github.com/nairadi) | Contributor |
| [Ryan Shankar](https://github.com/shankary) | Contributor |

---

*Originally built at BeaverHacks (May 2nd, 2026), now actively maintained as an open-source project.*