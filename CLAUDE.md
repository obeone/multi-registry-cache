# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-registry-cache is a Python package (v2.0.0) that generates a Docker Compose stack for running pull-through caches of multiple container registries (Docker Hub, GHCR, Quay, etc.) behind a Traefik reverse proxy with shared Redis blob caching.

## Commands

```bash
# Install in development mode (uses uv)
uv pip install -e ".[dev]"

# Run CLI
multi-registry-cache setup    # Interactive wizard → creates config.yaml
multi-registry-cache generate # Generates compose/ from config.yaml

# CLI options
multi-registry-cache setup --config path/to/config.yaml
multi-registry-cache generate --config config.yaml --output-dir compose

# Run tests
pytest

# Docker usage
docker run --rm -it -v $(pwd):/app obeoneorg/multi-registry-cache setup
docker run --rm -v $(pwd):/app obeoneorg/multi-registry-cache generate
```

## Architecture

Python package using Hatchling build system, Typer CLI, structured under `src/` layout.

### Package structure

```
src/multi_registry_cache/
├── __init__.py          # Package version (2.0.0)
├── cli.py               # Typer CLI entry point (setup/generate/completion subcommands)
├── generate.py          # Reads config.yaml, produces compose/ output files
├── setup_wizard.py      # Interactive wizard to create config.yaml
├── functions.py         # Shared library: service/router/config builders, YAML writing,
│                        #   string interpolation, HTTP secret generation
└── data/
    └── config.sample.yaml  # Bundled sample configuration template
```

Entry point: `multi-registry-cache` → `multi_registry_cache.cli:app`

### Config-to-output flow

```
config.yaml → generate.py → compose/
                               ├── compose.yaml    (Docker Compose: Traefik + Redis + N registry services)
                               ├── traefik.yaml     (hostname-based routing to each registry)
                               ├── {name}.yaml      (per-registry Distribution config)
                               ├── redis.conf       (database count = number of registries)
                               └── .env             (REGISTRY_HTTP_SECRET)
```

### Key concepts

- **Registry types**: `cache` (pull-through proxy with `proxy.remoteurl`) vs `registry` (standalone, no proxy block)
- **String interpolation**: `{name}`, `{url}`, `{username}`, `{password}`, `{ttl}` are replaced in per-registry templates from each registry's fields via `interpolate_strings()`
- **Redis DB assignment**: Each registry gets an incrementing Redis DB number (0, 1, 2...); `redis.conf` sets `databases N`
- **Config structure** (`config.yaml`): `registries[]`, `docker.baseConfig`, `docker.perRegistry.compose`, `traefik.baseConfig`, `traefik.perRegistry.router/service`, `registry.baseConfig` -- documented in `CONFIG.md`

### Runtime architecture

Traefik routes by hostname (e.g., `docker.example.com`) to the corresponding `registry:2` container, which either proxies upstream (cache) or serves directly (registry). All registries share one Redis instance with separate DB numbers.

## Testing

Tests are in `tests/` using pytest. Fixtures in `conftest.py` provide `sample_config`, `cache_registry`, `private_registry`, and `base_registry_config`. Tests cover `functions.py` utilities and `generate.py` output.

## CI/CD

GitHub Actions (`.github/workflows/build-and-publish.yaml`) builds multi-platform Docker images (`amd64`, `arm64`, `arm/v6-v8`, `i386`), pushes to Docker Hub and GHCR on `main` push or release, and signs with cosign. PRs trigger build-only (no push).

## Key files

- `pyproject.toml` -- Package metadata, dependencies, and build config (Hatchling)
- `config.sample.yaml` -- Reference configuration template (also bundled in package data)
- `config.yaml` -- User's live config (gitignored)
- `compose/` -- Generated output directory (gitignored)
- `docker/Dockerfile` -- Multi-stage build with `multi-registry-cache` as entrypoint
