# Changelog

All notable changes to XYZ will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-05-14

### Added

- Initial PyPI release
- Unified package list across pip, npm, and brew
- Interactive TUI with fuzzy search
- Package update and delete actions with dry-run confirmation
- AI package explainer powered by Google Gemini
- Natural language search (prefix with `?`)
- Orphan detection for pip, npm, and brew
- Dependency graph view
- Smart cleanup recommendations
- CVE scan feature

### Changed

- Migrated from BeaverHacks hackathon project to open-source
- Set up GitHub Actions CI (ruff, mypy, pytest)
- Enabled strict type checking with mypy

### Fixed

- Fixed mypy --strict errors in src/ code
- Fixed ruff linting errors

## [0.1.0-beaverhacks] — 2026-05-02

### Added

- Initial hackathon release (preserved as tag)
- Two-panel TUI layout with DataTable
- Package manager abstraction layer
- Gemini API integration for package explanations
- Keyboard navigation (j/k, arrows)
- Search with manager filtering

---

*Originally built at BeaverHacks (May 2nd, 2026), now actively maintained as an open-source project.*