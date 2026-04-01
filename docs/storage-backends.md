# Storage backends

The Distribution (registry:2) server supports several storage drivers for persisting image layers. Configure the driver under `registry.baseConfig.storage` in `config.yaml`.

> **Note:** `storage.cache.blobdescriptor: redis` is always configured separately and is independent of the storage driver. It tells the registry to cache blob *descriptors* (metadata) in Redis for fast repeated lookups. The storage driver handles the actual *layer data*.

---

## inmemory

Stores everything in RAM. Data is lost when the container restarts. Suitable for testing or ephemeral CI environments.

```yaml
registry:
  baseConfig:
    storage:
      cache:
        blobdescriptor: redis
      inmemory: {}
```

No additional configuration needed.

**Limitations:** No persistence. Not suitable for production. Memory usage grows unbounded as images are pulled.

---

## filesystem

Stores layers on the container's local filesystem. Requires a bind-mount to persist data across container restarts.

```yaml
registry:
  baseConfig:
    storage:
      cache:
        blobdescriptor: redis
      filesystem:
        rootdirectory: /var/lib/registry/{name}
```

The `{name}` placeholder gives each registry its own subdirectory, preventing cross-contamination.

### Adding the bind-mount

The setup wizard offers to add the bind-mount automatically. To add it manually, update `docker.perRegistry.compose.volumes` in `config.yaml`:

```yaml
docker:
  perRegistry:
    compose:
      volumes:
        - "./{name}.yaml:/etc/docker/registry/config.yml:ro"
        - "/var/lib/registry-cache/{name}:/var/lib/registry/{name}"
```

The host path (`/var/lib/registry-cache/{name}`) must exist and be writable by the container user (UID 1000 by default in `registry:2`).

```bash
sudo mkdir -p /var/lib/registry-cache
sudo chown -R 1000:1000 /var/lib/registry-cache
```

**Advantages:** Simple, no external dependencies.
**Limitations:** Single-host only. Disk space is consumed on the Docker host.

---

## S3

Stores layers in an S3-compatible object storage bucket. Works with AWS S3, MinIO, Ceph RADOS Gateway, Cloudflare R2, and other S3-compatible services.

```yaml
registry:
  baseConfig:
    storage:
      cache:
        blobdescriptor: redis
      s3:
        accesskey: AKIAIOSFODNN7EXAMPLE
        secretkey: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
        bucket: my-registry-cache
        region: eu-west-1
        regionendpoint: https://s3.amazonaws.com   # omit for AWS, set for other providers
        rootdirectory: "{name}"                    # per-registry prefix within the bucket
```

| Field | Required | Description |
|---|---|---|
| `accesskey` | Yes | S3 access key ID |
| `secretkey` | Yes | S3 secret access key |
| `bucket` | Yes | Bucket name (must already exist) |
| `region` | Yes | AWS region (e.g. `us-east-1`) or a placeholder value for non-AWS |
| `regionendpoint` | No | Custom endpoint URL — required for non-AWS S3-compatible services |
| `rootdirectory` | No | Key prefix within the bucket. Using `{name}` isolates each registry |

### Non-AWS S3-compatible services

```yaml
      s3:
        accesskey: minioadmin
        secretkey: minioadmin
        bucket: registry-cache
        region: us-east-1            # arbitrary value required by the client
        regionendpoint: https://minio.example.net
        rootdirectory: "{name}"
```

**Advantages:** Unlimited storage, highly durable, works across multiple hosts.
**Limitations:** Requires network access to the S3 endpoint. Latency on first pull from upstream depends on upload speed to S3.

---

## GCS

Stores layers in Google Cloud Storage.

```yaml
registry:
  baseConfig:
    storage:
      cache:
        blobdescriptor: redis
      gcs:
        bucket: my-registry-cache-bucket
        rootdirectory: "{name}"
        keyfile: |
          {
            "type": "service_account",
            "project_id": "my-project",
            ...
          }
```

| Field | Required | Description |
|---|---|---|
| `bucket` | Yes | GCS bucket name (must already exist) |
| `rootdirectory` | No | Object prefix within the bucket |
| `keyfile` | No | Service account JSON key. If omitted, Application Default Credentials are used (recommended for GKE) |

**Advantages:** Managed, durable, integrates with GCP IAM.
**Limitations:** GCP-specific. Egress costs apply for cross-region or cross-provider pulls.

---

## Choosing a backend

| Backend | Persistence | Multi-host | External dependency | Use case |
|---|---|---|---|---|
| `inmemory` | No | No | None | CI, testing |
| `filesystem` | Yes | No | None | Single-host production |
| `s3` | Yes | Yes | S3-compatible service | Multi-host, large scale |
| `gcs` | Yes | Yes | Google Cloud | GCP environments |

---

## Mixing backends across registries

The storage driver is defined in `registry.baseConfig`, which is shared across all registries. All registries use the same driver with per-registry subdirectories (via `{name}`). It is not possible to use different drivers for different registries in a single `config.yaml` without manual post-generation editing.
