# Contributing

Contributions are welcome. This page covers the development workflow, coding conventions, and the PR process.

---

## Development setup

```bash
git clone https://github.com/obeone/multi-registry-cache
cd multi-registry-cache

# Create a virtual environment and install all dependencies
uv sync

# Or install in editable mode with dev extras
uv pip install -e ".[dev]"
```

---

## Running tests

```bash
# All tests
uv run pytest

# Verbose
uv run pytest -v

# Single file
uv run pytest tests/test_functions.py
```

All new code must be accompanied by tests. See [Internals](internals.md) for the test structure.

---

## Linting

```bash
uv run ruff check src/ tests/
```

Fix auto-fixable issues:

```bash
uv run ruff check --fix src/ tests/
```

---

## Branch naming

| Change type | Branch prefix | Example |
| --- | --- | --- |
| New feature | `feat/` | `feat/gcs-storage` |
| Bug fix | `fix/` | `fix/redis-db-overflow` |
| Documentation | `docs/` | `docs/storage-backends` |
| Refactoring | `refactor/` | `refactor/interpolation` |
| Tests | `test/` | `test/generate-coverage` |
| Maintenance | `chore/` | `chore/deps-update` |

---

## Commit messages

This project uses [Conventional Commits](https://www.conventionalcommits.org/).

```text
<type>[optional scope]: <description>

[optional body]

[optional footer]
```

Examples:

```text
feat(storage): add GCS storage backend support
fix(generate): remove proxy block for registry type correctly
docs(storage): document S3 regionendpoint field
test(functions): add interpolate_strings edge cases
chore(deps): update PyYAML to 6.0.2
```

Rules:
- Use imperative mood (`add`, not `added` or `adds`)
- Keep the title under 72 characters
- Add a body only when the *why* is not obvious from the title
- Reference issues with `Closes #123` in the footer

---

## Pull request process

1. Fork the repository and create a branch from `main`.
2. Make your changes with granular, atomic commits.
3. Add or update tests to cover your change.
4. Run `pytest` and `ruff check` — both must pass.
5. Open a PR against `main` with a clear description of what and why.
6. A maintainer will review the PR. Address any requested changes.

---

## Adding a new registry type

The `type` field in `config.yaml` controls how the generator configures the Distribution proxy block. To add a new type:

1. Edit `functions.create_registry_config()` in `src/multi_registry_cache/functions.py` to handle the new type value.
2. Update `setup_wizard.py` if the wizard should offer the new type.
3. Add tests in `tests/test_functions.py` covering the new branch.
4. Document the type in [Configuration reference](configuration.md).

---

## Adding a storage driver to the wizard

The wizard's storage driver selection is in `setup_wizard.py` under the `Prompt.ask(..., choices=[...])` call. To add a new driver:

1. Add the driver name to the `choices` list.
2. Add an `elif storage_driver == "newdriver":` branch that collects required fields into `storage_config`.
3. Add tests in `tests/test_generate.py`.
4. Document the driver in [Storage backends](storage-backends.md).

---

## Reporting issues

Open an issue at [github.com/obeone/multi-registry-cache/issues](https://github.com/obeone/multi-registry-cache/issues). Include:

- The version of `multi-registry-cache` (`multi-registry-cache --version` — or the Docker image tag).
- Your `config.yaml` (redact credentials).
- The full error output.
- Steps to reproduce.
