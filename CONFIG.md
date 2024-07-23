# README

## Overview

This README provides detailed information about the configuration file `config.sample.yaml`. This file serves as a template for setting up a multi-registry environment with Docker Compose, Traefik, and a Redis cache. The configuration is divided into several sections, allowing for easy customization and management of multiple container registries.

## Table of Contents

- [README](#readme)
  - [Overview](#overview)
  - [Table of Contents](#table-of-contents)
  - [Configuration Breakdown](#configuration-breakdown)
    - [Registries Section](#registries-section)
    - [Docker Compose Configuration](#docker-compose-configuration)
      - [Base Config](#base-config)
      - [Per Registry Config](#per-registry-config)
    - [Traefik Configuration](#traefik-configuration)
      - [Base Config](#base-config-1)
    - [Registry Configuration](#registry-configuration)
    - [How to Use](#how-to-use)
      - [Automatic](#automatic)
      - [Manual](#manual)
  - [Conclusion](#conclusion)


## Configuration Breakdown

### Registries Section

The `registries` section defines the container registries that will be used. Each registry entry requires the following parameters:

- `name`: The name of the registry (used in Docker Compose).
- `url`: The URL of the registry.
- `username`: The username for the registry.
- `password`: The password for the registry.
- `ttl` (optional): Time-to-live for registry credentials.

Example:

```yaml
registries:
- name: dockerhub
  url: https://registry-1.docker.io
  username: user
  password: pass
- name: ghcr
  url: https://ghcr.io
  username: user
  password: pass
- name: nvcr
  url: https://nvcr.io
  username: user
  password: pass
- name: quay
  url: https://quay.io
  username: user
  password: pass
  ttl: 720h
```

### Docker Compose Configuration

The `docker` section is used to generate the `docker-compose.yaml` file. It consists of two sub-sections: `baseConfig` and `perRegistry`.

#### Base Config

Defines the base configuration for the Docker Compose file, including common services and networks.

```yaml
docker:
  baseConfig:
    version: '3.1'
    services:
      traefik:
        image: traefik:v2.10
        restart: always
        command:
        - '--providers.file.filename=/etc/traefik/traefik.yaml'
        ports:
        - '80:80'
        - '443:443'
        volumes:
        - './traefik.yaml:/etc/traefik/traefik.yaml:ro'
        - './acme:/etc/traefik/acme:rw'
        networks:
        - 'registries'
      redis:
        image: redis:7.2
        restart: always
        networks:
        - 'registries'
        volumes:
        - './redis.conf:/usr/local/etc/redis/redis.conf:ro'
        command:
        - redis-server
        - /usr/local/etc/redis/redis.conf
    networks:
      registries: {}
```

#### Per Registry Config

Defines services and settings that will be applied for each registry, using placeholders that will be replaced by actual values.

```yaml
  perRegistry:
    compose:
      image: registry:2
      restart: always
      volumes:
      - './{name}.yaml:/etc/docker/registry/config.yml:ro'
      networks:
      - registries
      environment:
      - 'REGISTRY_HTTP_SECRET=$REGISTRY_HTTP_SECRET'
```

### Traefik Configuration

The `traefik` section is used to generate the `traefik.yaml` file. It consists of two sub-sections: `baseConfig` and `perRegistry`.

#### Base Config

Defines the base Traefik configuration, including providers, entry points, logging, and optional TLS settings.

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
    http:
      routers: {}
      services: {}
    log:
      level: DEBUG
    accessLog: {}
  perRegistry:
    router:
      rule: "Host(`{name}.registry-cache.example.net`)"
      entryPoints:
      - web
      - websecure
      service: '{name}'
      tls: {}
    service:
      loadBalancer:
        servers:
        - url: "http://{name}:5000"
```

### Registry Configuration

The `registry` section configures the Docker registry itself, including health checks, storage, logging, and Redis caching.

```yaml
registry:
  baseConfig:
    version: '0.1'
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
    redis:
      addr: redis:6379
    proxy: {}
```

### How to Use

#### Automatic

- Run `python setup.py` and fine-tune settings in `config.yaml`after that.
- And run `python generate.py` to generate all files in `compose` directory.

#### Manual

1. Copy `config.sample.yaml` to `config.yaml`.
2. Fill in your registry credentials and other settings.
3. Set everything else (especially hosts)
4. Execute `python generate.py` to generate all files in `compose` directory.
5. Go in that directory (`cd compose`)
6. Run `docker compose up -d` to start the services.

By following these steps, you can configure and run your multi-registry environment with Traefik and Redis caching, simplifying the management of multiple container registries.

## Conclusion

The `config.sample.yaml` file serves as a flexible template to help you configure, manage, and deploy multiple container registries using Docker Compose, Traefik, and Redis. Customizing this file allows you to set up a robust and scalable container management environment tailored to your needs.

---

*Generated by GPT-4o*
