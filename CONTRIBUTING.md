# Contributing to eagendas Data Proxy

Thank you for your interest in contributing! This guide will help you get started.

## Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/<your-user>/eagendas-data-proxy.git
   cd eagendas-data-proxy
   ```
3. **Set up** the development environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   .venv\Scripts\activate      # Windows
   pip install -e ".[dev]"
   ```
4. **Start dependencies** (PostgreSQL + Redis):
   ```bash
   docker compose up -d db redis
   ```
5. **Run migrations**:
   ```bash
   alembic upgrade head
   ```

## Development Workflow

1. Create a branch from `main`:
   ```bash
   git checkout -b feat/my-feature
   ```
2. Make your changes
3. Run tests and linting:
   ```bash
   pytest
   ruff check .
   ruff format --check .
   ```
4. Commit using [Conventional Commits](https://www.conventionalcommits.org/):
   ```
   feat: add support for custom pseudonym prefix
   fix: handle missing email in PII enrichment
   docs: update configuration reference
   test: add webhook relay integration tests
   ```
5. Push and open a **Pull Request** against `main`

## Pull Request Guidelines

- Keep PRs focused on a single change
- Include tests for new features and bug fixes
- Update documentation if behavior changes
- Ensure all CI checks pass before requesting review

## Code Style

- Python 3.11+
- Linting and formatting: [Ruff](https://docs.astral.sh/ruff/) (config in `pyproject.toml`)
- Line length: 120 characters
- Async/await for all I/O operations

## Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_interceptor.py

# With verbose output
pytest -v
```

Tests use an in-memory SQLite database, so no external services are needed.

## Reporting Bugs

Open an issue with:
- Steps to reproduce
- Expected vs actual behavior
- Python version and OS
- Relevant logs or error messages

## Security Issues

**Do not open a public issue for security vulnerabilities.** See [SECURITY.md](SECURITY.md) for responsible disclosure instructions.

## License

By contributing, you agree that your contributions will be licensed under the [AGPL-3.0](LICENSE).
