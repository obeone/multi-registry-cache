# CLI reference

## Installation

### uvx (zero install, recommended for one-off use)

```bash
uvx multi-registry-cache setup
uvx multi-registry-cache generate
```

### uv tool / pipx (persistent install)

```bash
uv tool install multi-registry-cache
# or
pipx install multi-registry-cache
```

### pip

```bash
pip install multi-registry-cache
```

### Docker

```bash
# Interactive setup wizard
docker run --rm -ti \
  -v "./config.yaml:/app/config.yaml" \
  obeoneorg/multi-registry-cache setup

# Generate compose/ from an existing config.yaml
docker run --rm \
  -v "./config.yaml:/app/config.yaml" \
  -v "./compose:/app/compose" \
  obeoneorg/multi-registry-cache generate
```

The Docker image is available for `amd64`, `arm64`, `arm/v6`, `arm/v7`, `arm/v8`, and `i386`.

---

## Commands

### `setup`

Interactive wizard that creates a `config.yaml`.

```
multi-registry-cache setup [OPTIONS]
```

| Option | Short | Default | Description |
|---|---|---|---|
| `--config PATH` | `-c` | `config.yaml` | Path where the config file will be written |

The wizard asks for:

1. One or more **cache registries** (name, URL, credentials, TTL).
2. An optional **private registry** (standalone, no upstream).
3. A **domain name pattern** for Traefik routing (e.g. `{name}.registry-cache.example.net`).
4. A **storage driver** (`inmemory`, `filesystem`, `s3`, or `gcs`) with driver-specific settings.

After completing the wizard, review and fine-tune `config.yaml` before running `generate`. See [Configuration reference](configuration.md) for all available options.

---

### `generate`

Reads `config.yaml` and writes the full Docker Compose stack to the output directory.

```
multi-registry-cache generate [OPTIONS]
```

| Option | Short | Default | Description |
|---|---|---|---|
| `--config PATH` | `-c` | `config.yaml` | Path to the config file to read |
| `--output-dir DIR` | `-o` | `compose` | Directory where generated files are written |

Generated files:

| File | Description |
|---|---|
| `compose.yaml` | Docker Compose stack (Traefik + Redis + one service per registry) |
| `traefik.yaml` | Traefik dynamic configuration (routers + services) |
| `{name}.yaml` | Per-registry Distribution (registry:2) configuration |
| `redis.conf` | Redis configuration (`databases N`) |
| `.env` | `REGISTRY_HTTP_SECRET` (generated once, never overwritten) |
| `acme/` | Empty directory for Let's Encrypt certificate storage |

If a `docker-compose.yml` file exists in the output directory (legacy filename), the generator asks whether to remove it.

---

### `completion`

Prints a shell completion script.

```
multi-registry-cache completion [SHELL]
```

`SHELL` is one of `zsh`, `bash`, or `fish`. If omitted, auto-detected from the `$SHELL` environment variable.

#### Install completions

**zsh:**

```bash
multi-registry-cache completion zsh > ~/.zfunc/_multi-registry-cache
# Ensure ~/.zfunc is in your fpath — add to ~/.zshrc if needed:
# fpath=(~/.zfunc $fpath)
# autoload -Uz compinit && compinit
```

**bash:**

```bash
multi-registry-cache completion bash >> ~/.bashrc
source ~/.bashrc
```

**fish:**

```bash
multi-registry-cache completion fish > ~/.config/fish/completions/multi-registry-cache.fish
```

---

## Shell help

```bash
multi-registry-cache --help
multi-registry-cache setup --help
multi-registry-cache generate --help
```

---

## Typical workflow

```bash
# 1. Create config interactively
multi-registry-cache setup

# 2. Review and fine-tune
$EDITOR config.yaml

# 3. Generate the stack
multi-registry-cache generate --output-dir compose

# 4. Start the stack
cd compose && docker compose up -d
```

To use a non-default config path:

```bash
multi-registry-cache setup --config /etc/registry-cache/config.yaml
multi-registry-cache generate --config /etc/registry-cache/config.yaml --output-dir /etc/registry-cache/compose
```
