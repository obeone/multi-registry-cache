# Multi-Registry Pull Through Cache Setup Guide 🚀

Welcome to the Multi-Registry Pull Through Cache Setup Guide! This project is designed to help you create an efficient, bandwidth-saving local mirror for Docker Hub images and other container registries. By setting up a pull-through cache, you can significantly reduce internet traffic and improve the speed of image pulls for your containerized environments. 🌐💨

This script will generate a `docker-compose.yml` file. It will include one registry service for each registry mirror you wish to set up. A Traefik Proxy will be placed as a frontend for routing and providing a TLS endpoint. Additionally, a Redis service will be provided to enhance performance.

## Purpose of the Project 🎯

The primary goal of this project is to establish a local caching service that acts as an intermediary between your Docker daemons and public container image registries. This setup is perfect for environments with multiple instances of Docker or Kubernetes clusters, where each node pulling images separately can lead to unnecessary bandwidth consumption and latency. 🐳🔁

By using a pull-through cache, you can:
- Minimize external bandwidth usage
- Accelerate image pull times
- Reduce the load on public registries
- Ensure consistent availability of images within your network
- Reduce your carbon footprint

## How to Set Up the Project 🛠️

### Prerequisites
- Docker installed on your host machine
- `containerd` and/or `dockerd` running on your nodes
- Access to the internet to pull initial images
- Basic knowledge of Docker, Kubernetes, and container registries

### Step-by-Step Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-username/multi-registry-cache.git
   cd multi-registry-cache
   ```

2. **Set Up a Virtual Environment (Optional)**
   You may choose to create a virtual environment to avoid affecting your global Python package setup.
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Dependencies**
   Install the required packages using pip.
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the User-Friendly Setup**
   Execute the setup script to configure your registries and generate necessary files.
   ```bash
   python setup.py
   ```

5. **Review Advanced Configuration**
   After running the setup script, you should manually review the `config.yaml` file for advanced configurations such as TLS settings, Let's Encrypt, and more.
   ```bash
   nano config.yaml # or use your preferred text editor
   ```

6. **Generate Configuration Files**
   Run the generate script to create the necessary configuration files for your setup.
   ```bash
   python generate.py
   ```

7. **Start Your Services**
   Use Docker Compose to start your registry mirrors and the Traefik reverse proxy.
   ```bash
   cd compose
   docker compose up -d
   ```

## Configuring Container Runtimes 🔄

### containerd Configuration

For `containerd`, you'll need to modify the `config.toml` file to specify the registry mirrors.

```toml
[plugins."io.containerd.grpc.v1.cri".registry.mirrors]
  [plugins."io.containerd.grpc.v1.cri".registry.mirrors."docker.io"]
    endpoint = ["https://dockerhub.registry-cache.example.net"]
  [plugins."io.containerd.grpc.v1.cri".registry.mirrors."ghcr.io"]
    endpoint = ["https://ghcr.registry-cache.example.net"]
```

After updating the configuration, restart `containerd`:
```bash
sudo systemctl restart containerd
```

#### nerdctl Configuration

For `nerdctl`, you'll need to create a directory per registry mirror, and push content un a file :

```bash
mkdir -p /etc/containerd/certs.d/docker.io/
```

And create a file `/etc/containerd/certs.d/docker.io/hosts.toml` with the following content:

```toml
server = "https://docker.io"

[host."https://dockerhub.registry-cache.example.net"]
  capabilities = ["pull", "resolve"]
```

(Same principle in rootless mode, just modify user config)

### dockerd Configuration

For `dockerd`, you can only configure a single mirror for Docker Hub. Update the `/etc/docker/daemon.json` file with the following:

```json
{
  "registry-mirrors": ["https://dockerhub.registry-cache.example.net"]
}
```

Reload the Docker daemon to apply the changes:
```bash
sudo systemctl daemon-reload
sudo systemctl restart docker
```

### Kubernetes Clusters (k3s, RKE, RKE2 etc)

#### k3s / RKE2

Edit file `/etc/rancher/(k3s|rke2)/registries.yaml` and add :

```yaml
mirrors:
  docker.io:
    endpoint:
      - https://dockerhub.registry-cache.example.net
  ghcr.io:
    endpoint:
      - https://ghcr.registry-cache.example.net
```
#### Other distributions

For Kubernetes clusters, you'll probably need to configure each node's container runtime to use the registry mirror. Refer to the specific documentation of your distribution for details on how to apply registry mirror configurations.

## Conclusion 🎉

Congratulations! You've now set up a multi-registry pull-through cache that will serve as a local mirror for your container images. Enjoy faster image pulls, reduced external bandwidth, and a more resilient container environment!

---

Feel free to contribute to this project by submitting issues or pull requests. For questions or support, open an issue on the project's GitHub page. Happy caching! 🐋💾

---

**Keywords**: Docker, container registry, pull through cache, Docker Hub mirror, containerd, dockerd, Kubernetes, k3s, RKE, RKE2, image caching, setup guide, local mirror, container image optimization.
