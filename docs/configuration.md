# Configuration reference

The entire configuration lives in a single `config.yaml`. The file has four top-level sections:

```
config.yaml
├── registries[]          — list of registries to cache or host
├── docker                — Docker Compose base + per-registry template
├── traefik               — Traefik base + per-registry router/service template
└── registry              — Distribution (registry:2) base config template
```

Run `multi-registry-cache setup` to generate a starter file interactively, or copy `config.sample.yaml` and edit it manually.

---

## `registries[]`

List of registry definitions. Every field in each entry is available as a `{placeholder}` in the `perRegistry` templates.

```yaml
registries:
  - name: dockerhub          # (required) identifier — used in filenames, Compose service names, hostnames
    type: cache              # (required) "cache" or "registry"
    url: https://registry-1.docker.io   # upstream registry URL (cache type only)
    username: myuser         # upstream credentials (optional for public registries)
    password: mypassword     # written only to the per-registry Distribution config
    ttl: 720h                # how long to keep cached manifests (optional)
```

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Unique identifier. Used as the Compose service name, config filename (`{name}.yaml`), and in hostname interpolation. |
| `type` | Yes | `cache` — pull-through proxy. `registry` — standalone registry (no upstream). |
| `url` | For `cache` | Full URL of the upstream registry including scheme. |
| `username` / `password` | No | Credentials for the upstream registry. The password is stripped before Compose/Traefik interpolation. |
| `ttl` | No | Time-to-live for cached manifests (e.g. `168h`, `30d`). Passed to the Distribution `proxy.ttl` field. |

Additional custom fields (e.g. `region`, `zone`) can be added and used as `{region}` / `{zone}` in templates.

### Registry type: `cache`

The generator sets `registry.baseConfig.proxy.remoteurl` to the registry `url`, adds credentials if present, and adds `ttl` if present.

### Registry type: `registry`

The `proxy` block is entirely removed from the Distribution config. The container acts as a standalone private registry with no upstream.

---

## `docker`

Controls the generated `compose/compose.yaml`.

### `docker.baseConfig`

Full Docker Compose document that applies to all deployments. Defines the shared infrastructure services (Traefik, Redis) and networks. Per-registry services are **merged in** at generation time.

```yaml
docker:
  baseConfig:
    services:
      traefik:
        image: traefik:v2.10
        restart: always
        command:
          - "--providers.file.filename=/etc/traefik/traefik.yaml"
        ports:
          - "80:80"
          - "443:443"
        volumes:
          - "./traefik.yaml:/etc/traefik/traefik.yaml:ro"
          - "./acme:/etc/traefik/acme:rw"
        networks:
          - "registries"
      redis:
        image: redis:7.2
        restart: always
        networks:
          - "registries"
        volumes:
          - "./redis.conf:/usr/local/etc/redis/redis.conf:ro"
        command:
          - redis-server
          - /usr/local/etc/redis/redis.conf
    networks:
      registries: {}
```

You can add any valid Docker Compose fields here (healthchecks, resource limits, logging drivers, etc.).

To pass environment variables for Traefik ACME DNS challenges:

```yaml
      traefik:
        environment:
          - 'RFC2136_NAMESERVER=$RFC2136_NAMESERVER'
          - 'RFC2136_TSIG_SECRET=$RFC2136_TSIG_SECRET'
```

### `docker.perRegistry.compose`

Template applied to **each registry**. Supports `{placeholder}` interpolation using any field from the registry entry.

```yaml
  perRegistry:
    compose:
      image: registry:2
      restart: always
      volumes:
        - "./{name}.yaml:/etc/docker/registry/config.yml:ro"
      networks:
        - registries
      environment:
        - "REGISTRY_HTTP_SECRET=$REGISTRY_HTTP_SECRET"
```

The resulting service is added to `compose.yaml` under `services.{name}`.

To add a bind-mount for filesystem storage (created automatically by the wizard):

```yaml
      volumes:
        - "./{name}.yaml:/etc/docker/registry/config.yml:ro"
        - "/var/lib/registry-cache/{name}:/var/lib/registry-cache/{name}"
```

---

## `traefik`

Controls the generated `compose/traefik.yaml`. Traefik reads this file as its dynamic configuration provider.

### `traefik.baseConfig`

Base Traefik configuration. The generator merges per-registry routers and services into `http.routers` and `http.services`.

```yaml
traefik:
  baseConfig:
    providers:
      file:
        filename: /etc/traefik/traefik.yaml
    entryPoints:
      web:
        address: ":80"
      websecure:
        address: ":443"
        transport:
          respondingTimeouts:
            readTimeout: 0s    # disable — required for large image downloads
            writeTimeout: 0s
            idleTimeout: 0s
    http:
      routers: {}    # populated by the generator
      services: {}   # populated by the generator
    log:
      level: DEBUG
    accessLog: {}
```

**Why `readTimeout: 0s`?** Registry pulls transfer large layer blobs. If Traefik enforces a response timeout the connection is killed mid-transfer. Setting the timeouts to `0s` disables them for the HTTPS entry point.

To enable HTTP → HTTPS redirect:

```yaml
      web:
        address: ":80"
        http:
          redirections:
            entryPoint:
              to: websecure
              scheme: https
              permanent: true
```

To configure Let's Encrypt (see [TLS & SSL](tls-ssl.md) for the full guide):

```yaml
    certificatesResolvers:
      mydnschallenge:
        acme:
          email: me@example.net
          storage: /etc/traefik/acme/acme.json
          dnsChallenge:
            provider: rfc2136
            delayBeforeCheck: 30
            resolvers:
              - "1.1.1.1:53"
```

### `traefik.perRegistry`

Templates for the Traefik router and service created for each registry.

```yaml
  perRegistry:
    router:
      rule: "Host(`{name}.registry-cache.example.net`)"
      entryPoints:
        - web
        - websecure
      service: "{name}"
      tls: {}          # empty = use default TLS; remove key to disable TLS

    service:
      loadBalancer:
        servers:
          - url: "http://{name}:5000"
```

| Field | Notes |
|---|---|
| `router.rule` | Must contain `{name}` so each registry gets a unique hostname. |
| `router.tls` | Empty dict enables TLS with the default certificate. Add `certResolver: mydnschallenge` for ACME. Remove the key entirely for HTTP-only. |
| `service.loadBalancer.servers[].url` | Points to the Docker Compose service name (`{name}`) on port 5000. |

---

## `registry`

Controls the per-registry Distribution config files written to `compose/{name}.yaml`.

### `registry.baseConfig`

Template applied to every registry. The generator deep-copies this, applies type-specific logic (proxy block), assigns the Redis DB number, then interpolates `{placeholders}`.

```yaml
registry:
  baseConfig:
    version: "0.1"
    health:
      storagedriver:
        enabled: true
        interval: 10s
        threshold: 3
    http:
      addr: :5000
      headers:
        X-Content-Type-Options:
          - nosniff
    log:
      fields:
        service: registry
    storage:
      cache:
        blobdescriptor: redis    # always use Redis for blob descriptor caching
      # storage driver goes here — see Storage backends
    redis:
      addr: redis:6379
      # db is set automatically by the generator — do not set it manually
    proxy: {}    # filled in for cache type, removed for registry type
```

`storage.cache.blobdescriptor: redis` tells the Distribution server to cache blob descriptors in Redis. This is independent of the storage driver used to persist image layers.

For available storage drivers see [Storage backends](storage-backends.md).

---

## Annotated full example

```yaml
registries:
  - name: dockerhub
    type: cache
    url: https://registry-1.docker.io
    username: myuser
    password: mypassword
    ttl: 720h

  - name: ghcr
    type: cache
    url: https://ghcr.io
    username: myuser
    password: ghp_mytoken

  - name: private
    type: registry        # standalone, no upstream

docker:
  baseConfig:
    services:
      traefik:
        image: traefik:v2.10
        restart: always
        command:
          - "--providers.file.filename=/etc/traefik/traefik.yaml"
        ports:
          - "80:80"
          - "443:443"
        volumes:
          - "./traefik.yaml:/etc/traefik/traefik.yaml:ro"
          - "./acme:/etc/traefik/acme:rw"
        networks:
          - "registries"
      redis:
        image: redis:7.2
        restart: always
        networks:
          - "registries"
        volumes:
          - "./redis.conf:/usr/local/etc/redis/redis.conf:ro"
        command:
          - redis-server
          - /usr/local/etc/redis/redis.conf
    networks:
      registries: {}

  perRegistry:
    compose:
      image: registry:2
      restart: always
      volumes:
        - "./{name}.yaml:/etc/docker/registry/config.yml:ro"
      networks:
        - registries
      environment:
        - "REGISTRY_HTTP_SECRET=$REGISTRY_HTTP_SECRET"

traefik:
  baseConfig:
    providers:
      file:
        filename: /etc/traefik/traefik.yaml
    entryPoints:
      web:
        address: ":80"
      websecure:
        address: ":443"
        transport:
          respondingTimeouts:
            readTimeout: 0s
            writeTimeout: 0s
            idleTimeout: 0s
    http:
      routers: {}
      services: {}
    log:
      level: INFO
    accessLog: {}

  perRegistry:
    router:
      rule: "Host(`{name}.registry-cache.example.net`)"
      entryPoints:
        - web
        - websecure
      service: "{name}"
      tls: {}
    service:
      loadBalancer:
        servers:
          - url: "http://{name}:5000"

registry:
  baseConfig:
    version: "0.1"
    health:
      storagedriver:
        enabled: true
        interval: 10s
        threshold: 3
    http:
      addr: :5000
      headers:
        X-Content-Type-Options:
          - nosniff
    log:
      fields:
        service: registry
    storage:
      cache:
        blobdescriptor: redis
      filesystem:
        rootdirectory: /var/lib/registry/{name}
    redis:
      addr: redis:6379
    proxy: {}
```
