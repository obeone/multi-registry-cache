# Internals & developer guide

This page documents the source code structure and explains how the generator pipeline works end to end.

---

## Package layout

```text
src/multi_registry_cache/
├── __init__.py        # package version constant
├── cli.py             # Typer app — command definitions and shell completion scripts
├── generate.py        # reads config.yaml, produces compose/ output files
├── setup_wizard.py    # interactive wizard — prompts user, writes config.yaml
├── functions.py       # shared utilities called by generate.py
└── data/
    └── config.sample.yaml   # bundled template, loaded by setup_wizard.py
```

Entry point registered in `pyproject.toml`:

```toml
[project.scripts]
multi-registry-cache = "multi_registry_cache.cli:app"
```

---

## `cli.py` — command dispatch

`cli.py` defines a Typer application with three subcommands: `setup`, `generate`, and `completion`.

**Lazy imports** — `setup_wizard.main` and `generate.generate` are imported inside the command functions, not at module level. This keeps CLI startup fast regardless of which command is invoked.

**Static shell completions** — rather than using Typer's built-in completion (which requires runtime introspection), completion scripts for `zsh`, `bash`, and `fish` are hardcoded as string constants (`_ZSH_COMPLETION`, `_BASH_COMPLETION`, `_FISH_COMPLETION`). The `completion` subcommand prints the appropriate script. Auto-detection of the current shell uses the `$SHELL` environment variable.

---

## `setup_wizard.py` — interactive configuration

The wizard uses `ruamel.yaml` (instead of `PyYAML`) to load the bundled `config.sample.yaml` and write the final `config.yaml`. `ruamel.yaml` preserves comments, quote styles, and indentation — this means the generated `config.yaml` retains the helpful inline comments from the sample file.

**Flow:**

1. Load `data/config.sample.yaml` via `importlib.resources` (works correctly when installed as a package or run from Docker).
2. Clear `config['registries']` and prompt the user to define registries in a loop.
3. Optionally add a `registry`-type (private) entry.
4. Prompt for the Traefik domain pattern and write it to `traefik.perRegistry.router.rule`.
5. Prompt for the storage driver; collect driver-specific fields; write them to `registry.baseConfig.storage`.
6. For `filesystem` storage, optionally append the bind-mount to `docker.perRegistry.compose.volumes`.
7. Write the final config to `config_path` (or a temp file if the user declines).
8. Print the next command (`multi-registry-cache generate` or the Docker equivalent, detected via `$IN_DOCKER`).

---

## `generate.py` — file generation

`generate(config_path, output_dir)` is the core function. It:

1. Loads `config.yaml` with `yaml.safe_load`.
2. Extracts the six top-level config sections.
3. Creates `output_dir/acme/` if needed.
4. Iterates over `registries[]`:
   - Deep-copies `registry.baseConfig` to avoid mutating shared state.
   - Calls `functions.create_registry_config()` to apply type logic, Redis DB, and interpolation.
   - Writes `output_dir/{name}.yaml`.
   - Strips `password` from the registry dict.
   - Calls `functions.create_docker_service()` and `functions.create_traefik_router()` / `functions.create_traefik_service()`, merging results into the running `docker_config` / `traefik_config` dicts.
   - Increments `count_redis_db`.
5. Writes `compose.yaml`, `traefik.yaml`, `redis.conf` (`databases N`).
6. If `docker-compose.yml` exists in the output dir, asks the user whether to remove it.
7. Calls `functions.write_http_secret()` to write `REGISTRY_HTTP_SECRET` to `.env`.

---

## `functions.py` — shared utilities

### `interpolate_strings(obj, variables)`

Recursively walks `dict`, `list`, and `str` values and calls `str.format_map(variables)` on every string. Non-string leaves are returned unchanged. This is the mechanism behind all `{name}`, `{url}`, `{ttl}` substitutions.

### `create_docker_service(registry, custom)`

Merges `custom` (the `docker.perRegistry.compose` template) into a new dict and runs `interpolate_strings` with the registry fields as variables. Returns the interpolated service definition.

### `create_traefik_router(registry, custom)`

Same pattern as `create_docker_service` but for `traefik.perRegistry.router`.

### `create_traefik_service(registry, custom)`

Same pattern for `traefik.perRegistry.service`.

### `create_registry_config(config, registry, db)`

Applies type-specific logic before interpolation:

- `type == 'cache'`: sets `config['proxy']['remoteurl']`, adds `username`/`password` if present, adds `ttl` if present.
- any other type: deletes the `proxy` key entirely.

Then runs `interpolate_strings`, and finally sets `config['redis']['db'] = int(db)` on the already-interpolated dict (the DB number is an integer, not a string template).

### `write_yaml_file(filename, data)`

Serialises `data` to YAML using `yaml.dump` (PyYAML) and writes to `filename` with UTF-8 encoding.

### `write_to_file(filename, data)`

Writes a plain string to `filename`. Used for `redis.conf`.

### `write_http_secret(output_dir)`

Checks whether `REGISTRY_HTTP_SECRET` already exists in `output_dir/.env`. If not, appends a new 32-byte hex token generated with `secrets.token_hex(32)`. Idempotent — never overwrites an existing secret.

---

## Test suite

Tests live in `tests/` and use pytest.

```text
tests/
├── conftest.py          # shared fixtures
├── test_functions.py    # unit tests for functions.py
└── test_generate.py     # integration tests for generate.py
```

### Fixtures (`conftest.py`)

| Fixture | Description |
| --- | --- |
| `sample_config` | Full parsed `config.yaml`-like dict with two registries |
| `cache_registry` | Single cache-type registry dict |
| `private_registry` | Single registry-type dict (no upstream) |
| `base_registry_config` | Minimal Distribution config dict |

### Running tests

```bash
# With uv (recommended)
uv run pytest

# Or with the activated venv
pytest

# Verbose output
pytest -v

# Run a single test file
pytest tests/test_functions.py
```

### Linting

```bash
ruff check src/ tests/
```

---

## Development setup

```bash
git clone https://github.com/obeone/multi-registry-cache
cd multi-registry-cache

# Create venv and install all dependencies including dev extras
uv sync

# Install in editable mode (alternative)
uv pip install -e ".[dev]"

# Run the CLI from the venv
uv run multi-registry-cache --help
```
