# syntax=docker/dockerfile:1
#
# Multi-stage Dockerfile for the multi-registry-cache CLI tool.
# Builds the package in a full image, then copies the installed artifacts
# into a slim runtime image for a smaller final image.

# -- Build stage --
FROM python:3.12-slim AS builder

WORKDIR /build

COPY . .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefix=/install .

# -- Runtime stage --
FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/obeone/multi-registry-cache" \
      org.opencontainers.image.description="Multi-registry pull-through cache configuration generator" \
      org.opencontainers.image.licenses="MIT"

ENV IN_DOCKER=1

WORKDIR /app

# Copy installed package from builder
COPY --from=builder /install /usr/local

# Non-root user
RUN groupadd -r -g 10001 app && useradd -r -u 10001 -g app -d /app app
USER app

ENTRYPOINT ["multi-registry-cache"]
