# Upgrading to v2.0.0

## What changed

v2.0.0 restructures the project from standalone Python scripts into a proper installable CLI package. The configuration format and Docker image interface are unchanged.

## Breaking changes

| v1.x | v2.0.0 |
| --- | --- |
| `python setup.py` | `multi-registry-cache setup` |
| `python generate.py` | `multi-registry-cache generate` |
| `pip install -r requirements.txt` | `pip install multi-registry-cache` |
| Clone the repo to use it | Install with `uvx`, `pipx`, or `pip` |

## What is NOT affected

- **`config.yaml` format** — 100% compatible, no changes needed
- **Docker usage** — `docker run ... setup` and `docker run ... generate` work exactly as before
- **Generated output** — same `compose/` files, same Traefik/registry configs

## How to upgrade

### If you use Docker (most users)

Nothing to do. Pull the latest image and everything works as before:

```bash
docker run --rm -ti -v "./config.yaml:/app/config.yaml" -v "./compose:/app/compose" obeoneorg/multi-registry-cache generate
```

### If you run the scripts directly

1. Install the CLI:

   ```bash
   uv tool install multi-registry-cache
   # or: pipx install multi-registry-cache
   # or: pip install multi-registry-cache
   ```

2. Replace your commands:

   ```bash
   # Before
   python setup.py
   python generate.py

   # After
   multi-registry-cache setup
   multi-registry-cache generate
   ```

3. Your existing `config.yaml` works as-is.

### If you cloned the repo

The repo no longer has `setup.py`, `generate.py`, or `functions.py` at the root. If you were running scripts from a git clone:

1. Pull the latest code
2. Install the package locally: `pip install .` (or `uv sync` for development)
3. Use `multi-registry-cache setup` / `multi-registry-cache generate` instead of `python setup.py` / `python generate.py`

## New features in v2.0.0

- **Installable CLI** — `uvx multi-registry-cache`, no clone needed
- **`--config` / `-c` option** — specify a custom config file path
- **`--output-dir` / `-o` option** — specify a custom output directory
- **Shell completion** — `multi-registry-cache completion zsh > ~/.zfunc/_multi-registry-cache`
- **Test suite** — 28 unit and integration tests
- **CI testing** — pytest runs before Docker image build
- **Smaller Docker image** — multi-stage build, non-root user
