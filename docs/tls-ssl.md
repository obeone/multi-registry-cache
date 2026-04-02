# TLS & SSL

Traefik handles TLS termination for all registry endpoints. This page covers the available approaches: Let's Encrypt via DNS challenge, bring-your-own certificate, and HTTP-only (no TLS).

---

## How TLS is configured

TLS is controlled in two places in `config.yaml`:

1. **`traefik.baseConfig`** — global TLS settings: certificate resolvers, default certificates.
2. **`traefik.perRegistry.router.tls`** — per-router TLS activation (present = TLS enabled; absent = HTTP only).

The `acme/` directory is created by the generator unconditionally. Traefik stores Let's Encrypt certificates as `acme/acme.json`.

---

## Let's Encrypt via DNS challenge (recommended)

DNS challenges allow wildcard certificates and work without exposing port 80 to the internet.

### 1. Configure a certificate resolver in `traefik.baseConfig`

```yaml
traefik:
  baseConfig:
    certificatesResolvers:
      mydnschallenge:
        acme:
          email: me@example.net
          storage: /etc/traefik/acme/acme.json
          dnsChallenge:
            provider: rfc2136          # or cloudflare, route53, ovh, etc.
            delayBeforeCheck: 30       # seconds to wait after DNS propagation
            resolvers:
              - "1.1.1.1:53"
              - "8.8.8.8:53"
```

Supported DNS providers: see [Traefik ACME DNS challenge providers](https://doc.traefik.io/traefik/https/acme/#providers).

### 2. Pass provider credentials to Traefik

Add the required environment variables under `docker.baseConfig.services.traefik.environment`:

```yaml
docker:
  baseConfig:
    services:
      traefik:
        environment:
          - 'RFC2136_NAMESERVER=$RFC2136_NAMESERVER'
          - 'RFC2136_TSIG_ALGORITHM=$RFC2136_TSIG_ALGORITHM'
          - 'RFC2136_TSIG_KEY=$RFC2136_TSIG_KEY'
          - 'RFC2136_TSIG_SECRET=$RFC2136_TSIG_SECRET'
```

These reference variables from the shell environment or a `.env` file at `compose/.env`.

### 3. Enable wildcard certificate (optional but recommended)

Instead of issuing one certificate per registry subdomain, use a single wildcard certificate in `traefik.baseConfig`:

```yaml
    tls:
      stores:
        default:
          defaultGeneratedCert:
            resolver: mydnschallenge
            domain:
              main: registry-cache.example.net
              sans:
                - '*.registry-cache.example.net'
```

### 4. Reference the resolver in per-registry routers

```yaml
traefik:
  perRegistry:
    router:
      rule: "Host(`{name}.registry-cache.example.net`)"
      entryPoints:
        - websecure
      service: "{name}"
      tls:
        certResolver: mydnschallenge
```

### 5. Redirect HTTP to HTTPS (optional)

```yaml
    entryPoints:
      web:
        address: ":80"
        http:
          redirections:
            entryPoint:
              to: websecure
              scheme: https
              permanent: true
```

---

## Bring-your-own certificate

If you manage certificates externally (e.g. cert-manager, Vault PKI, manual renewal):

### 1. Mount the certificate files into Traefik

```yaml
docker:
  baseConfig:
    services:
      traefik:
        volumes:
          - "./traefik.yaml:/etc/traefik/traefik.yaml:ro"
          - "./acme:/etc/traefik/acme:rw"
          - "/etc/ssl/registry-cache:/certs:ro"   # your cert directory
```

### 2. Reference the certificates in `traefik.baseConfig`

```yaml
traefik:
  baseConfig:
    tls:
      certificates:
        - certFile: /certs/fullchain.pem
          keyFile: /certs/privkey.pem
```

### 3. Keep `tls: {}` in per-registry routers

The router picks up the certificate from the TLS store automatically:

```yaml
traefik:
  perRegistry:
    router:
      tls: {}
```

---

## HTTP only (no TLS)

Remove the `tls` key from the per-registry router and remove the `websecure` entry point:

```yaml
traefik:
  baseConfig:
    entryPoints:
      web:
        address: ":80"
    # no websecure entry point

  perRegistry:
    router:
      rule: "Host(`{name}.registry-cache.example.net`)"
      entryPoints:
        - web
      service: "{name}"
      # no tls key
```

> **Warning:** HTTP-only exposes registry credentials and image manifests in plaintext. Do not use in production or on untrusted networks.

---

## The `acme/` directory

The generator creates `compose/acme/` at every run. Traefik writes `acme/acme.json` there to persist obtained certificates across restarts. If the file does not exist Traefik creates it on first start.

Ensure the `acme/` directory is writable by the Traefik container:

```bash
chmod 700 compose/acme
```

Traefik sets `acme.json` permissions to 600 automatically.

---

## Self-signed certificate (development)

For local development, let Traefik generate a self-signed certificate automatically. Set `tls: {}` in the router and add no certificate resolver. Traefik uses its built-in self-signed cert. Clients will see a TLS warning that must be accepted or bypassed (`--insecure-skip-tls-verify` in containerd, `DOCKER_TLS_VERIFY` for dockerd).
