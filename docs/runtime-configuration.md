# Runtime configuration

Once the cache stack is running, configure your container runtimes to pull through it. Each runtime needs to know that requests for `docker.io`, `ghcr.io`, etc. should be redirected to your cache endpoints.

Assuming your domain pattern is `{name}.registry-cache.example.net`, the endpoints would be:

| Registry | Cache endpoint |
| --- | --- |
| Docker Hub (`docker.io`) | `https://dockerhub.registry-cache.example.net` |
| GHCR (`ghcr.io`) | `https://ghcr.registry-cache.example.net` |
| Quay (`quay.io`) | `https://quay.registry-cache.example.net` |

---

## containerd

Edit `/etc/containerd/config.toml` (create if absent):

```toml
version = 2

[plugins."io.containerd.grpc.v1.cri".registry]
  [plugins."io.containerd.grpc.v1.cri".registry.mirrors]
    [plugins."io.containerd.grpc.v1.cri".registry.mirrors."docker.io"]
      endpoint = ["https://dockerhub.registry-cache.example.net"]
    [plugins."io.containerd.grpc.v1.cri".registry.mirrors."ghcr.io"]
      endpoint = ["https://ghcr.registry-cache.example.net"]
    [plugins."io.containerd.grpc.v1.cri".registry.mirrors."quay.io"]
      endpoint = ["https://quay.registry-cache.example.net"]
```

Apply the change:

```bash
sudo systemctl restart containerd
```

---

## nerdctl

nerdctl uses a per-registry `hosts.toml` file under `/etc/containerd/certs.d/`.

```bash
sudo mkdir -p /etc/containerd/certs.d/docker.io
sudo mkdir -p /etc/containerd/certs.d/ghcr.io
```

`/etc/containerd/certs.d/docker.io/hosts.toml`:

```toml
server = "https://registry-1.docker.io"

[host."https://dockerhub.registry-cache.example.net"]
  capabilities = ["pull", "resolve"]
```

`/etc/containerd/certs.d/ghcr.io/hosts.toml`:

```toml
server = "https://ghcr.io"

[host."https://ghcr.registry-cache.example.net"]
  capabilities = ["pull", "resolve"]
```

No restart needed — nerdctl reads the files on each pull.

---

## dockerd

Edit `/etc/docker/daemon.json` (create if absent):

```json
{
  "registry-mirrors": [
    "https://dockerhub.registry-cache.example.net"
  ]
}
```

> **Note:** `dockerd` `registry-mirrors` only redirects Docker Hub (`docker.io`) pulls. For other registries (GHCR, Quay, etc.) use containerd or nerdctl configuration instead.

Apply the change:

```bash
sudo systemctl daemon-reload && sudo systemctl restart docker
```

---

## k3s

Create or edit `/etc/rancher/k3s/registries.yaml`:

```yaml
mirrors:
  docker.io:
    endpoint:
      - https://dockerhub.registry-cache.example.net
  ghcr.io:
    endpoint:
      - https://ghcr.registry-cache.example.net
  quay.io:
    endpoint:
      - https://quay.registry-cache.example.net
```

Apply the change:

```bash
sudo systemctl restart k3s
# or on agent nodes:
sudo systemctl restart k3s-agent
```

---

## RKE2

Create or edit `/etc/rancher/rke2/registries.yaml` (same format as k3s):

```yaml
mirrors:
  docker.io:
    endpoint:
      - https://dockerhub.registry-cache.example.net
  ghcr.io:
    endpoint:
      - https://ghcr.registry-cache.example.net
```

Apply the change:

```bash
sudo systemctl restart rke2-server
# or on agent nodes:
sudo systemctl restart rke2-agent
```

---

## BuildKit / docker buildx

BuildKit resolves images independently from dockerd. Without explicit configuration, `docker build` does **not** use `daemon.json` registry mirrors.

### Create a `buildkitd.toml`

```toml
[registry."docker.io"]
  mirrors = ["dockerhub.registry-cache.example.net"]

[registry."ghcr.io"]
  mirrors = ["ghcr.registry-cache.example.net"]

[registry."quay.io"]
  mirrors = ["quay.registry-cache.example.net"]

# If the cache endpoint uses a self-signed or private CA:
# [registry."dockerhub.registry-cache.example.net"]
#   ca = ["/etc/certs/my-ca.pem"]
```

### Where to place the file

| Context | Config path |
| --- | --- |
| Docker Engine (rootful) | `/etc/buildkit/buildkitd.toml` |
| Docker Engine (rootless) | `~/.config/buildkit/buildkitd.toml` |
| buildx default builder | `~/.docker/buildx/buildkitd.default.toml` |
| Docker Desktop | Not supported (see below) |

### Docker Desktop

The default builder in Docker Desktop uses the `docker` driver, which does **not** support `buildkitd.toml`. Create a separate builder with the `docker-container` driver:

```bash
docker buildx create \
  --use \
  --bootstrap \
  --name cached-builder \
  --driver docker-container \
  --buildkitd-config /path/to/buildkitd.toml
```

Verify:

```bash
docker buildx ls
# cached-builder   docker-container   running
```

All subsequent `docker build` or `docker buildx build` commands will use this builder and the configured mirrors.

---

## Other Kubernetes distributions

For distributions not listed above, configure the underlying container runtime on each node:

- **containerd-based** (Talos, Flatcar, most managed K8s): see [containerd](#containerd) section above.
- **CRI-O**: edit `/etc/containers/registries.conf` to add `[[registry]]` mirror entries.
- **Managed K8s** (EKS, GKE, AKS): node configuration depends on the managed node image. Consult your cloud provider's documentation for custom containerd config.

---

## Verifying the cache is used

Pull an image through the cache and check the registry container logs:

```bash
docker pull dockerhub.registry-cache.example.net/library/alpine:latest
# or with a configured mirror:
docker pull alpine:latest

# Check logs
docker compose -f compose/compose.yaml logs dockerhub --tail=20
```

On a cache hit the log shows a local response with no upstream request. On a cache miss you will see a request to the upstream registry URL.
