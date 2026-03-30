"""Tests for multi_registry_cache.functions module."""

import copy
import os

import pytest

from multi_registry_cache.functions import (
    create_docker_service,
    create_registry_config,
    create_traefik_router,
    create_traefik_service,
    interpolate_strings,
    write_http_secret,
    write_to_file,
    write_yaml_file,
)


class TestInterpolateStrings:
    """Tests for the interpolate_strings function."""

    def test_interpolate_string(self):
        result = interpolate_strings("{name}.example.com", {"name": "docker"})
        assert result == "docker.example.com"

    def test_interpolate_dict(self):
        obj = {"host": "{name}.example.com", "port": 5000}
        result = interpolate_strings(obj, {"name": "ghcr"})
        assert result == {"host": "ghcr.example.com", "port": 5000}

    def test_interpolate_list(self):
        obj = ["{name}-a", "{name}-b"]
        result = interpolate_strings(obj, {"name": "test"})
        assert result == ["test-a", "test-b"]

    def test_interpolate_nested(self):
        obj = {"services": [{"url": "http://{name}:5000"}]}
        result = interpolate_strings(obj, {"name": "registry"})
        assert result == {"services": [{"url": "http://registry:5000"}]}

    def test_passthrough_non_string(self):
        assert interpolate_strings(42, {"name": "x"}) == 42
        assert interpolate_strings(None, {"name": "x"}) is None
        assert interpolate_strings(True, {"name": "x"}) is True

    def test_multiple_variables(self):
        result = interpolate_strings("{name}:{port}", {"name": "host", "port": "8080"})
        assert result == "host:8080"


class TestCreateRegistryConfig:
    """Tests for create_registry_config."""

    def test_cache_registry_sets_proxy(self, base_registry_config, cache_registry):
        result = create_registry_config(base_registry_config, cache_registry, 0)
        assert result["proxy"]["remoteurl"] == "https://registry-1.docker.io"
        assert result["proxy"]["username"] == "testuser"
        assert result["proxy"]["password"] == "testpass"
        assert result["proxy"]["ttl"] == "720h"

    def test_cache_registry_sets_redis_db(self, base_registry_config, cache_registry):
        result = create_registry_config(base_registry_config, cache_registry, 3)
        assert result["redis"]["db"] == 3

    def test_private_registry_removes_proxy(self, base_registry_config, private_registry):
        result = create_registry_config(base_registry_config, private_registry, 1)
        assert "proxy" not in result

    def test_private_registry_sets_redis_db(self, base_registry_config, private_registry):
        result = create_registry_config(base_registry_config, private_registry, 2)
        assert result["redis"]["db"] == 2

    def test_cache_without_credentials(self, base_registry_config):
        registry = {"name": "nocreds", "type": "cache", "url": "https://example.com"}
        result = create_registry_config(base_registry_config, registry, 0)
        assert result["proxy"]["remoteurl"] == "https://example.com"
        assert "username" not in result["proxy"]

    def test_interpolation_happens(self, base_registry_config, cache_registry):
        result = create_registry_config(base_registry_config, cache_registry, 0)
        # The registry name should be interpolated in any {name} placeholders
        for value in _flatten_strings(result):
            assert "{name}" not in value


class TestCreateDockerService:
    """Tests for create_docker_service."""

    def test_basic_service(self):
        registry = {"name": "docker"}
        custom = {"image": "registry:2", "volumes": ["./{name}.yaml:/config.yml:ro"]}
        result = create_docker_service(registry, custom)
        assert result["image"] == "registry:2"
        assert result["volumes"] == ["./docker.yaml:/config.yml:ro"]

    def test_empty_custom(self):
        result = create_docker_service({"name": "test"})
        assert result == {}


class TestCreateTraefikRouter:
    """Tests for create_traefik_router."""

    def test_router_interpolation(self):
        registry = {"name": "ghcr"}
        custom = {"rule": "Host(`{name}.example.com`)", "service": "{name}"}
        result = create_traefik_router(registry, custom)
        assert result["rule"] == "Host(`ghcr.example.com`)"
        assert result["service"] == "ghcr"


class TestCreateTraefikService:
    """Tests for create_traefik_service."""

    def test_service_interpolation(self):
        registry = {"name": "quay"}
        custom = {"loadBalancer": {"servers": [{"url": "http://{name}:5000"}]}}
        result = create_traefik_service(registry, custom)
        assert result["loadBalancer"]["servers"][0]["url"] == "http://quay:5000"


class TestWriteYamlFile:
    """Tests for write_yaml_file."""

    def test_writes_valid_yaml(self, tmp_path):
        import yaml

        data = {"key": "value", "list": [1, 2, 3]}
        filepath = str(tmp_path / "test.yaml")
        write_yaml_file(filepath, data)

        with open(filepath) as f:
            loaded = yaml.safe_load(f)
        assert loaded == data


class TestWriteToFile:
    """Tests for write_to_file."""

    def test_writes_text(self, tmp_path):
        filepath = str(tmp_path / "test.txt")
        write_to_file(filepath, "databases 5")

        with open(filepath) as f:
            assert f.read() == "databases 5"


class TestWriteHttpSecret:
    """Tests for write_http_secret."""

    def test_creates_env_file(self, tmp_path):
        write_http_secret(str(tmp_path))
        env_path = tmp_path / ".env"
        assert env_path.exists()
        content = env_path.read_text()
        assert "REGISTRY_HTTP_SECRET=" in content
        # Secret should be 64 hex chars (32 bytes)
        secret = content.strip().split("=")[1]
        assert len(secret) == 64

    def test_idempotent(self, tmp_path):
        write_http_secret(str(tmp_path))
        first_content = (tmp_path / ".env").read_text()

        write_http_secret(str(tmp_path))
        second_content = (tmp_path / ".env").read_text()

        # Should not append a second secret
        assert first_content == second_content


def _flatten_strings(obj):
    """Recursively yield all string values from a nested dict/list structure."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _flatten_strings(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from _flatten_strings(item)
