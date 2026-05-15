# Contributing to XYZ

Welcome to XYZ! We're excited that you want to contribute. This guide will help you get started with the development workflow and coding standards.

## GitHub Flow

We follow GitHub Flow - all changes must go through pull requests. **Direct pushes to `main` are not allowed.**

### Workflow

1. **Fork** the repository
2. **Create** a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/bug-description
   ```
3. **Make** your changes, following our coding standards
4. **Test** your changes locally:
   ```bash
   pytest tests/
   ruff check src/ tests/
   mypy src/
   ```
5. **Commit** your changes with clear commit messages
6. **Push** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
7. **Open** a pull request against `main`
8. **Address** review feedback and wait for CI to pass

## Development Setup

### Requirements

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or `venv`

### Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/xyz.git
cd xyz

# Create virtual environment
uv venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -e ".[dev]"
```

### Running Locally

```bash
# Run the app
xyz
# or
python -m xyz

# Run tests
pytest

# Run linter
ruff check src/ tests/

# Run type checker
mypy src/
```

## Coding Standards

### Type Checking

We use **mypy** with strict mode. All code in `src/` must pass:

```bash
mypy src/
```

### Linting

We use **ruff** for linting. Check passes if:

```bash
ruff check src/ tests/
```

### Code Style

- Follow PEP 8
- Use type hints everywhere in `src/`
- Use `builtins.list` instead of `list` if shadowing with a method named `list`
- Keep lines under 100 characters
- Use descriptive variable names

### Commit Messages

Use clear, descriptive commit messages:

```
feat: add bulk upgrade functionality for Shift+U

Implemented the actual execution logic for upgrading all outdated
packages instead of just showing a notification. Added proper error
handling and progress tracking.

Fixes #12
```

Types:
- `feat:` - new feature
- `fix:` - bug fix
- `refactor:` - code refactoring
- `docs:` - documentation
- `ci:` - CI/CD changes
- `test:` - test additions/changes
- `chore:` - maintenance

## Pull Request Requirements

Before opening a PR, ensure:

- [ ] All tests pass: `pytest tests/`
- [ ] Linting passes: `ruff check src/ tests/`
- [ ] Type checking passes: `mypy src/`
- [ ] PR description explains the changes and motivation
- [ ] New features have tests (if applicable)

## PR Review Process

1. All CI checks must pass (tests, linting, type checking)
2. At least one maintainer approval required
3. Address any feedback promptly
4. Once approved, maintainers will merge

## Getting Help

- Open an [issue](https://github.com/xyz-tui/xyz/issues) for bugs or feature requests
- Join discussions in pull requests

We appreciate your contributions!