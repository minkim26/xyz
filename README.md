# XYZ — Universal Dependency Manager

> One terminal. Every package manager. No more context switching.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Textual](https://img.shields.io/badge/TUI-Textual-6e40c9?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Hackathon%20MVP-orange)

---

## What is XYZ?

XYZ is a terminal-based dependency manager that gives you a single interactive interface across all your package managers. Instead of juggling `pip list`, `brew info`, `npm ls`, and `pacman -Q` in separate sessions, XYZ aggregates everything into one searchable, actionable TUI — powered by AI.

Select an unfamiliar package and XYZ will tell you exactly what it is, why it's probably on your machine, and whether it's safe to remove. No browser. No tab switching. No guessing.

---

## Features (MVP)

- **Unified package list** — aggregates packages from all supported managers into one view
- **Fuzzy search** — filter across all packages in real time as you type
- **Update / Delete** — manage packages in-place with a dry-run preview before any destructive action
- **Orphan detection** — flags packages with no remaining dependents
- **AI package explainer** — select any package for a plain-English explanation via Gemini API
- **Package detail pane** — version, install source, size, and dependent count at a glance

---

## Supported Package Managers

| Manager | Platform |
|---|---|
| `pip` | Python (all platforms) |
| `brew` | macOS / Linux |
| `npm` | Node.js (all platforms) |
| `apt` | Debian / Ubuntu |
| `pacman` | Arch Linux |
| `bun` | JavaScript (all platforms) |

---

## Getting Started

### Requirements

- Python 3.10+
- One or more of the supported package managers installed

### Install

```bash
pip install xyz-manager
```

### Run

```bash
xyz
```

### Gemini API Key (for AI explainer)

```bash
export GEMINI_API_KEY=your_key_here
xyz
```

Without a key, XYZ runs fully in offline mode — all features except the AI explainer remain available.

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
- [ ] **Post-MVP** — `cargo`, `conda`, `pipx`, `gem`, `winget` support

---

## Team

| Name | Email |
|---|---|
| Minsu Kim | kimminsu@oregonstate.edu |
| Adithya Nair | nairadi@oregonstate.edu |
| Ryan Shankar | shankary@oregonstate.edu |

---

## License

MIT — do whatever you want with it.

---

*Built at BeaverHacks · May 2nd, 2026*