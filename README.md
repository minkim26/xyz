# XYZ — Universal Dependency Manager

<p align="center"><img src="assets/xyz-logo-dark.svg" width="100%" alt="XYZ logo"></p>



> One terminal. Every package manager. No more context switching.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Textual](https://img.shields.io/badge/TUI-Textual-6e40c9?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Hackathon%20MVP-orange)

---

## What is XYZ?

XYZ is a terminal-based dependency manager that gives you a single interactive interface across your package managers. Instead of juggling `pip list`, `brew info`, and `npm ls` in separate sessions, XYZ aggregates everything into one searchable, actionable TUI — powered by AI.

Select an unfamiliar package and XYZ will tell you exactly what it is, why it's probably on your machine, and whether it's safe to remove. No browser. No tab switching. No guessing.

---

## Features

- **Unified package list** — aggregates installed packages from detected managers into one view
- **Live search + manager filtering** — substring filtering, manager pills, and orphan-only toggle
- **Natural language AI search** — prefix search with `?` (e.g., `?AI` or `?database`) to find packages by intent using Gemini
- **Safe package actions** — update/delete with dry-run preview modal before confirmation
- **Auto-refresh after actions** — package list re-scans after updates/deletes
- **Orphan detection (non-AI)** — manager-native orphan checks for `pip`, `npm`, and `brew`
- **AI package explainer (streaming)** — streamed Gemini explanations in the detail pane
- **Smart cleanup recommendations** — Gemini-powered remove/review suggestions
- **Dependency graph view** — dependency graph preview + fullscreen modal (when `mermaid-ascii` is available)
- **CVE scan** — Gemini Search-grounded vulnerability summary for selected package

---

## Keybindings

- `↑/↓` — navigate package list
- `u` — update selected package
- `d` — delete selected package
- `U` — upgrade-all placeholder (notification only; bulk upgrade execution not yet implemented)
- `a` — fetch AI explanation
- `s` — scan selected package for CVEs
- `g` — view dependency graph
- `o` — toggle orphan packages filter
- `m` — cycle manager filter
- `c` — run smart cleanup analysis
- `/` — focus search bar (prefix search with `?` for AI search)
- `esc` — blur search or close modals
- `ctrl+q` — quit

---

## Supported Package Managers

| Manager | Platform |
|---|---|
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
```

You can also run as a module:

```bash
python -m xyz
```

### Gemini API Key (for AI explainer)

```bash
export GEMINI_API_KEY=your_key_here
xyz
```

Without a key, XYZ runs in offline mode: package listing/search/filtering and package actions remain available; AI features (AI search, explainer, smart cleanup, CVE scan) are disabled.

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
git clone https://github.com/minkim26/xyz.git
cd xyz
pip install -e .
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
```

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| TUI Framework | [Textual](https://github.com/Textualize/textual) |
| AI Integration | Google Gemini API |
| Package parsing | Native subprocess calls per manager |
| Distribution | pip / PyPI |

---

## Roadmap

- [ ] **v1.1** — Snapshot & restore (export full package state to `packages.toml`, restore on new machine)
- [ ] **v1.2** — CVE security overlay via OSV API
- [ ] **v1.3** — Duplicate detection (same package across multiple managers)
- [ ] **v1.4** — Audit trail with install-reason annotations
- [ ] **v1.5** — Bulk upgrade execution for `U` (currently UI placeholder)
- [ ] **Post-MVP** — expand manager coverage (`apt`, `pacman`, `bun`, `cargo`, `conda`, `pipx`, `gem`, `winget`)

---

## Team

| Name | Email |
|---|---|
| Minsu Kim | kimminsu@oregonstate.edu |
| Adithya Nair | nairadi@oregonstate.edu |
| Ryan Shankar | shankary@oregonstate.edu |

---

## License

MIT. See [LICENSE](LICENSE) for the full text.

---

*Built at BeaverHacks · May 2nd, 2026*
