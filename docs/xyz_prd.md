# XYZ — Universal Dependency Manager



### Product Requirements Document

| Field | Value |
|---|---|
| Status | Draft |
| Version | 0.2 |
| Stage | Hackathon MVP |
| Hackathon | BeaverHacks |
| Last Updated | May 2026 |

---

## Table of Contents

1. [Overview](#1-overview)
2. [The Problem](#2-the-problem)
3. [Competitive Landscape & Differentiation](#3-competitive-landscape--differentiation)
4. [Goals & Non-Goals](#4-goals--non-goals)
5. [Target Users](#5-target-users)
6. [Feature Requirements](#6-feature-requirements-mvp)
7. [Supported Package Managers](#7-supported-package-managers-mvp)
8. [Tech Stack](#8-tech-stack)
9. [MVP Success Metrics](#9-mvp-success-metrics)
10. [Risks & Mitigations](#10-risks--mitigations)
11. [Hackathon Strategy & Track Targeting](#11-hackathon-strategy--track-targeting)
12. [24-Hour Development Timeline & Task Assignments](#12-24-hour-development-timeline--task-assignments)
13. [Future Roadmap](#13-future-roadmap-post-mvp)
14. [Elevator Pitch](#14-elevator-pitch)
15. [Appendix: Glossary](#appendix-glossary)

---

## 1. Overview

XYZ is a terminal-based, interactive dependency management tool that gives developers a single pane of glass across all their package managers. Instead of jumping between `pip list`, `brew info`, `npm ls`, and `pacman -Q` in separate terminal sessions, XYZ aggregates everything into one searchable, actionable TUI — with an AI layer powered by Google Gemini that explains what each package is and whether it is safe to remove.

The core premise is simple: developers should not have to remember which tool manages which package. XYZ handles that mapping so they can focus on building.

---

## 2. The Problem

### 2.1 Dependency Hell Is a Multi-Manager Problem

Python is infamous for its environment fragmentation, but the real problem is wider. A typical developer machine in 2026 runs packages managed by at least four different tools simultaneously (e.g. Homebrew, pip, npm, and apt). None of these tools are aware of each other.

This creates three distinct pain points:

- **Visibility gap** — there is no unified way to answer "what version of X do I have installed?"
- **Orphan bloat** — packages installed as transitive dependencies accumulate silently after their parent is removed.
- **Cognitive overhead** — developers must recall the correct syntax for every package manager's list, update, and remove commands.

### 2.2 Existing Workarounds Fall Short

Several partial solutions exist but none address the full problem:

- **Shell aliases** — quick to set up, impossible to maintain across teams or machines.
- **Spreadsheet inventories** — manual, instantly stale, not actionable.
- **Docker containers** — solve isolation for projects, not for the developer's own system tooling.
- **Reading raw command output** — the status quo, and the experience XYZ is designed to replace.

---

## 3. Competitive Landscape & Differentiation

### 3.1 Feature Comparison

| Feature | XYZ (MVP) | Topgrade | mise / asdf | Nix | Renovate |
|---|:---:|:---:|:---:|:---:|:---:|
| Unified multi-manager view | ✓ | ✗ | ✗ | ✗ | ✗ |
| Interactive TUI / fzf search | ✓ | ✗ | ✗ | ✗ | ✗ |
| AI package explainer | ✓ | ✗ | ✗ | ✗ | ✗ |
| Install / update packages | ✓ | ✓ (update only) | ✗ | ✓ | ✗ |
| Delete / remove packages | ✓ | ✗ | ✗ | ✓ | ✗ |
| Supports pip / npm / brew etc | ✓ | ✓ | Runtimes only | Nix pkgs only | ✗ |
| Orphan detection | ✓ | ✗ | ✗ | Partial | ✗ |
| Snapshot & restore | ✓ (planned) | ✗ | ✗ | Partial | ✗ |
| Works without config files | ✓ | ✓ | ✗ | ✗ | ✗ |
| Project-specific scope | ✗ | ✗ | ✓ | ✓ | ✓ |

### 3.2 Why XYZ Is Different

**Topgrade**
The closest conceptual relative. It is a Rust CLI that runs upgrades across all package managers in one command. However it is entirely non-interactive — there is no search, no package inspection, no delete workflow, and no unified view of what is installed. It runs and exits. XYZ treats the package list as a workspace, not a one-shot command.

**mise / asdf**
These tools manage language runtime versions (Node 20 vs 22, Python 3.11 vs 3.12). They are orthogonal to XYZ — they do not manage packages within a runtime. A developer using mise still needs XYZ to see what pip or npm packages they have installed.

**Nix / NixOS**
Nix solves dependency management at the OS level with hermetic, reproducible builds. It is a legitimate long-term solution but requires adopting an entirely new package ecosystem and a steep learning curve. It is not practical for the majority of developers doing rapid iteration across mixed environments. XYZ works with the package managers developers already use.

**Renovate / Dependabot**
These tools operate at the project level inside a Git repository. They are CI/CD automation tools for keeping project dependency files (`package.json`, `requirements.txt`) up to date. They have no concept of system-wide packages and require a hosted repository to function. XYZ is a local, system-level tool that requires no external service.

### 3.3 XYZ's Unique Position

XYZ occupies a gap that none of these tools fill: an interactive, system-wide, multi-manager TUI that supports search, update, and delete — without requiring the developer to change how they install software. It is additive. It works on top of whatever managers a developer already uses, and layers AI context on top so developers understand what they have, not just that they have it.

---

## 4. Goals & Non-Goals

### 4.1 Goals (MVP)

- Provide a unified, searchable list of all installed packages across supported package managers.
- Allow in-TUI update, upgrade, and delete of individual packages.
- Ship a fast, keyboard-driven fzf-style search experience.
- Display package metadata: version, install source, and size where available.
- Detect and flag orphaned packages with no remaining dependents.
- Support a minimum of six package managers: Homebrew, apt, Pacman, pip, npm, and Bun.
- Integrate Google Gemini API for plain-English package explanations and orphan risk assessment.

### 4.2 Non-Goals (MVP)

- Snapshot and restore (planned for v1.1).
- CVE / security advisory integration (planned for v1.2).
- Cross-machine sync or cloud storage.
- GUI / web interface.
- Language runtime version management (defer to mise/asdf).

---

## 5. Target Users

- Full-stack and backend developers maintaining multiple active projects.
- DevOps and platform engineers managing developer workstations.
- Power users who work across multiple package ecosystems daily.
- Developers migrating between machines who want a portable package inventory.

---

## 6. Feature Requirements (MVP)

### 6.1 Unified Package View

- On launch, XYZ scans all supported package managers and aggregates results into a single list.
- Each entry displays: package name, version, managing tool, and size.
- Packages are grouped by manager by default; grouping can be toggled off.
- Scans run concurrently per manager via `asyncio` to minimise startup latency.

### 6.2 Fuzzy Search

- fzf-style incremental search filters the list in real time as the user types.
- Search matches on package name and description.
- Results are ranked by relevance score (prefix matches surface first).

### 6.3 Package Actions

- **Update** — update a selected package to its latest available version.
- **Upgrade all** — run upgrade across all managers simultaneously with a progress view.
- **Delete** — remove a selected package; prompts for confirmation before executing.
- All destructive actions show a dry-run preview before execution.

### 6.4 Orphan Detection

- XYZ flags packages that were installed as dependencies but whose parent package has since been removed.
- Orphans are surfaced in a dedicated filter view with a one-key delete option.

### 6.5 Package Detail Pane

- Selecting a package opens a split detail pane showing: full version string, install date (where available), dependents, and install source URL.

### 6.6 AI Package Explainer (Gemini)

- Selecting any package triggers a Gemini API call that returns a plain-English summary: what the package does, why it is likely installed, and whether it is safe to remove.
- **Natural language search** — users can type queries like "anything related to machine learning" and Gemini maps the intent to matching package names across all managers.
- **Orphan risk assessment** — when XYZ flags an orphaned package, Gemini explains whether removing it carries risk based on the package's known dependents and common use cases.
- All AI calls are non-blocking; the TUI remains fully interactive while Gemini responds.
- XYZ degrades gracefully with no API key — all features except the AI explainer remain available.

---

## 7. Supported Package Managers (MVP)

| Manager | Platform |
|---|---|
| Homebrew | macOS / Linux |
| apt | Debian / Ubuntu |
| Pacman | Arch Linux |
| pip / pip3 | Python (all platforms) |
| npm | Node.js (all platforms) |
| Bun | JavaScript (all platforms) |

Post-MVP candidates: `pipx`, `conda`, `cargo`, `gem`, `dnf`, `winget`.

---

## 8. Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| Language | Python 3.10+ | Team expertise; fastest path to a working demo |
| TUI Framework | [Textual](https://github.com/Textualize/textual) | CSS-like layout, built-in widgets, asyncio-native |
| AI Integration | Google Gemini API | Hackathon track target; generous free tier |
| Package parsing | Native subprocess calls per manager | No extra dependencies; manager CLI is the source of truth |
| Concurrency | `asyncio` + `asyncio.gather` | Non-blocking concurrent manager scans |
| Distribution | pip / PyPI | Simplest install story: `pip install xyz-manager` |

### Why Textual over Rust (Ratatui) or Go (Bubbletea)

Rust and Go produce faster binaries with smaller memory footprints (~4–8 MB vs ~35–50 MB for Python). However, for XYZ's use case this difference is imperceptible:

- **Startup time** — Textual apps launch in under 400ms. Acceptable for a tool users spend minutes inside.
- **Render speed** — Textual achieves 60fps on modern terminals via delta-rendering. Identical to Go and Rust TUIs in practice.
- **Concurrency** — XYZ's bottleneck is subprocess I/O, not CPU. Python's `asyncio` handles concurrent manager scans without hitting the GIL.
- **Distribution** — the only real trade-off. Rust/Go compile to a single binary; Textual requires Python 3.10+. Mitigated by publishing to PyPI (`pip install xyz-manager`) and optionally bundling a binary via PyInstaller post-hackathon.

The team's Python expertise means faster iteration, fewer bugs under time pressure, and a more polished final demo — which matters more than binary size in a 24-hour hackathon.

---

## 9. MVP Success Metrics

- Unified package list loads within 3 seconds on a machine with 500+ packages across all managers.
- Fuzzy search returns results within 50ms of each keystroke.
- All six target package managers return correct data in the demo environment.
- Gemini package explainer returns a response within 3 seconds of package selection.
- Hackathon judges can install, search, and delete a package without reading documentation.

---

## 10. Risks & Mitigations

| Risk | Description | Mitigation |
|---|---|---|
| Manager CLI variance | Package managers output in different formats across OS versions. | Parse each manager independently with isolated parsers; test each one before integrating. |
| Privilege escalation | Delete and update often require `sudo`. | Prompt for sudo inline; never cache credentials. |
| Destructive actions | Deleting the wrong package can break the system. | Mandatory dry-run preview and confirmation prompt for all destructive operations. |
| Scan performance | Slow managers (pip, conda) can block the UI. | Run all manager scans concurrently with `asyncio.gather` and per-manager timeouts. |
| Gemini API latency | AI calls could block or slow the TUI. | All Gemini calls run in background async workers; TUI never waits on them. |
| Python not installed | Target machine may lack Python 3.10+. | Document requirement clearly; post-MVP, bundle with PyInstaller. |

---

## 11. Hackathon Strategy & Track Targeting

### Primary Track: Google Gemini — Best Use of Gemini API

XYZ targets the Gemini track by integrating conversational AI directly into the dependency management workflow. The AI layer is not decorative — it solves a genuine gap that the TUI alone cannot: **context**. A package name like `libsodium` or `py4j` means nothing to most developers without research. Gemini closes that gap inline, without leaving the terminal.

The three Gemini integration points each demonstrate a distinct capability:

- **Package Explainer** — tool use + knowledge retrieval in a single prompt
- **Natural Language Search** — intent mapping across unstructured package names
- **Orphan Risk Assessment** — reasoning under uncertainty with a concrete actionable output

This is Gemini doing something genuinely useful that no current dependency tool does, making it a strong fit for the "creative and effective application" framing of the track.

### Secondary Track: Beginner

If all team members are first-time hackathon participants, XYZ is also a strong Beginner track submission. The project demonstrates clear ambition (a multi-manager TUI is non-trivial), has a concrete learning arc (terminal rendering, concurrent process execution, API integration), and solves a real problem the team personally experiences. The Beginner track narrative should emphasise what broke, what was learned, and why the team chose a technically difficult problem for their first event.

### Demo Flow (Judges spend 3–5 minutes per project)

The winning demo loop is: **launch → search → select unknown package → Gemini explains it → delete with confirmation.** This 15-second sequence shows the unified view, the AI explainer, and the safety guardrails all in one pass. Record it as a GIF and put it at the top of the README and submission page.

---

## 12. 24-Hour Development Timeline & Task Assignments

> **Philosophy:** Ship a working demo with one tight, impressive user flow rather than a broad but shallow feature set. The goal is one moment that is undeniably cool.

---

### 👤 Teammate 1 — Package Manager Abstraction Layer

**Hours 0–4: Foundation**
- Define the shared `Package` dataclass: `name`, `version`, `manager`, `size`, `is_orphan`
- Implement abstract base class `BaseManager` with `list()`, `update()`, `delete()`, `check_orphans()` methods
- Implement `pip` and `npm` parsers against the base class
- Write a `ManagerRegistry` that `asyncio.gather`s all manager scans on launch

**Hours 4–10: Manager Breadth**
- Implement `brew` parser
- Implement `apt` parser (Linux)
- Add per-manager timeouts and error handling so one failing manager never blocks the UI
- Deliver a clean JSON/dataclass payload that the TUI layer can consume without knowing which manager produced it

**Hours 16–20: Stretch**
- Add `pacman` and/or `bun` support if time allows
- Implement orphan detection logic per manager

---

### 👤 Teammate 2 — TUI Shell & Layout

**Hours 0–4: Scaffold**
- Bootstrap the Textual app: `App`, `Header`, `Footer`, keybinding map
- Set up the two-panel layout: package list (left) and detail pane (right)
- Wire the `ManagerRegistry` output into a `DataTable` widget with columns: name, manager, version, size

**Hours 4–10: Interactivity**
- Implement fzf-style incremental search bar — filters the `DataTable` in real time
- Add manager filter toggle (show all / show one manager)
- Navigation with arrow keys and vim keys (`j`/`k`)
- Orphan filter view (`O` key) that narrows list to flagged packages

**Hours 10–16: Actions**
- Update action (`U`) — calls manager's `update()`, shows inline progress
- Delete action (`D`) — shows dry-run modal, waits for confirmation, then executes
- Upgrade all (`Shift+U`) — fans out update across all managers with a progress bar per manager

---

### 👤 Teammate 3 — AI Integration (Gemini)

**Hours 0–4: API Setup**
- Set up Gemini API client with key from environment variable (`GEMINI_API_KEY`)
- Implement graceful fallback — if no key present, detail pane shows "Set GEMINI_API_KEY to enable AI explanations"
- Write the core `explain_package(name, manager, version)` async function

**Hours 4–10: Package Explainer**
- Integrate explainer into the detail pane — triggers when a package is selected
- Show a loading indicator in the pane while Gemini responds
- Prompt engineering: the response must answer three things — what it does, why it's likely installed, and is it safe to remove

**Hours 10–16: Natural Language Search + Orphan Assessment**
- Implement natural language search mode (triggered by `?` prefix in search bar)
- Write `assess_orphan_risk(name, manager)` for the orphan risk assessment
- Surface the orphan assessment automatically when an orphaned package is selected

**Hours 16–20: Polish**
- Cap Gemini response length for the detail pane
- Add error handling for rate limits and network failures
- Test all three Gemini flows end-to-end in the demo environment

---

### 👤 Teammate 4 — Distribution, Demo & Documentation

**Hours 0–4: Repo Setup**
- Initialise the GitHub repo, branch strategy, and `pyproject.toml`
- Set up `pip install -e .` local dev install so all teammates can run the app from source
- Write the project `README.md` skeleton with install instructions

**Hours 10–16: Integration**
- Keep `main` branch stable — merge teammates' branches, resolve conflicts
- Smoke test the full app end-to-end after each major merge

**Hours 20–23: Ship It**
- Publish to PyPI (`python -m build && twine upload`)
- Set up custom Homebrew tap (`brew tap yourname/xyz`) pointing to the PyPI release
- Record the demo GIF: launch → search → select unknown package → Gemini explains → delete with confirmation
- Write the final submission description

**Hour 23–24: Rehearsal**
- Run the live demo twice with the full team watching
- Confirm the demo machine has `GEMINI_API_KEY` set and all six package managers present
- Know exactly which keystrokes hit which actions — terminal demos fail silently

---

## 13. Future Roadmap (Post-MVP)

### v1.1 — Snapshot & Restore
- Export full package state to a `packages.toml` manifest file.
- Restore from manifest on a new machine in one command.
- Diff two snapshots to see what changed between environments.

### v1.2 — Security Overlay
- Integrate with the OSV (Open Source Vulnerabilities) API to flag CVEs across all installed packages.
- Surface a risk score per manager and per package.

### v1.3 — Duplicate Detection
- Flag packages present under the same name across multiple managers.
- Suggest a canonical manager for each duplicate and offer to consolidate.

### v1.4 — Audit Trail
- Lightweight install-reason annotation: tag packages with a project or reason at install time.
- Queryable log of all XYZ actions (installs, deletes, upgrades) with timestamps.

### v2.0 — Binary Distribution
- Bundle with PyInstaller for a single-binary release.
- Add `cargo`, `conda`, `pipx`, `gem`, `dnf`, `winget` support.

---

## 14. Elevator Pitch

*For a non-technical audience — 30 seconds:*

> "You know how your phone has one App Store where you can see everything installed, update apps, and delete the ones you don't need anymore? Developers don't have that. They might have six or seven completely separate systems managing their software, and none of them talk to each other. XYZ is that App Store for developers — one place to see everything installed on your machine, search it, clean it up, and even ask AI why something is there in the first place. It saves the kind of 20-minute debugging session that happens when you can't remember what you installed six months ago."

---

## Appendix: Glossary

| Term | Definition |
|---|---|
| TUI | Terminal User Interface. An interactive, keyboard-driven interface rendered in the terminal. |
| Orphan | A package installed as a dependency that is no longer required by any explicitly installed package. |
| fzf | A popular terminal fuzzy finder. XYZ's search UX is modelled on its interaction pattern. |
| asyncio | Python's built-in async I/O library. Used in XYZ to run all manager scans concurrently. |
| CVE | Common Vulnerabilities and Exposures. A public database of known security vulnerabilities. |
| OSV | Open Source Vulnerabilities. A vulnerability database and API maintained by Google. |
| Textual | A Python TUI framework by Textualize. Provides a CSS-like layout engine and reusable widgets. |
| PyInstaller | A tool that bundles a Python app and its interpreter into a single executable binary. |