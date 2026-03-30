"""Integration tests for the generate command."""

import os
import shutil

import yaml
import pytest

from multi_registry_cache.generate import generate


class TestGenerate:
    """Integration tests for the full generate pipeline."""

    def test_generate_creates_all_files(self, tmp_path):
        """Run generate with sample config and verify all expected output files are created."""
        output_dir = str(tmp_path / "compose")
        generate(config_path="config.sample.yaml", output_dir=output_dir)

        # Check all expected files exist
        expected_files = [
            "compose.yaml",
            "traefik.yaml",
            "redis.conf",
            ".env",
            "dockerhub.yaml",
            "ghcr.yaml",
            "nvcr.yaml",
            "quay.yaml",
            "private.yaml",
        ]
        for filename in expected_files:
            filepath = os.path.join(output_dir, filename)
            assert os.path.exists(filepath), f"Expected file {filename} not found"

        # Check acme directory exists
        assert os.path.isdir(os.path.join(output_dir, "acme"))

    def test_compose_yaml_has_all_services(self, tmp_path):
        """Verify the generated compose.yaml contains all registry services."""
        output_dir = str(tmp_path / "compose")
        generate(config_path="config.sample.yaml", output_dir=output_dir)

        with open(os.path.join(output_dir, "compose.yaml")) as f:
            compose = yaml.safe_load(f)

        services = compose["services"]
        # Should have traefik, redis, plus each registry
        assert "traefik" in services
        assert "redis" in services
        assert "dockerhub" in services
        assert "ghcr" in services
        assert "nvcr" in services
        assert "quay" in services
        assert "private" in services

    def test_traefik_yaml_has_routers_and_services(self, tmp_path):
        """Verify the generated traefik.yaml contains router and service entries."""
        output_dir = str(tmp_path / "compose")
        generate(config_path="config.sample.yaml", output_dir=output_dir)

        with open(os.path.join(output_dir, "traefik.yaml")) as f:
            traefik = yaml.safe_load(f)

        routers = traefik["http"]["routers"]
        services = traefik["http"]["services"]
        for name in ["dockerhub", "ghcr", "nvcr", "quay", "private"]:
            assert name in routers, f"Router for {name} not found"
            assert name in services, f"Service for {name} not found"

    def test_redis_conf_has_correct_db_count(self, tmp_path):
        """Verify redis.conf has the correct number of databases."""
        output_dir = str(tmp_path / "compose")
        generate(config_path="config.sample.yaml", output_dir=output_dir)

        with open(os.path.join(output_dir, "redis.conf")) as f:
            content = f.read()
        assert content == "databases 5"  # 5 registries in sample config

    def test_cache_registry_has_proxy(self, tmp_path):
        """Verify cache-type registry configs include proxy settings."""
        output_dir = str(tmp_path / "compose")
        generate(config_path="config.sample.yaml", output_dir=output_dir)

        with open(os.path.join(output_dir, "dockerhub.yaml")) as f:
            config = yaml.safe_load(f)
        assert "proxy" in config
        assert config["proxy"]["remoteurl"] == "https://registry-1.docker.io"

    def test_private_registry_has_no_proxy(self, tmp_path):
        """Verify private (non-cache) registry configs do not include proxy settings."""
        output_dir = str(tmp_path / "compose")
        generate(config_path="config.sample.yaml", output_dir=output_dir)

        with open(os.path.join(output_dir, "private.yaml")) as f:
            config = yaml.safe_load(f)
        assert "proxy" not in config

    def test_passwords_not_in_compose_yaml(self, tmp_path):
        """Verify that passwords are not leaked into compose.yaml or traefik.yaml."""
        output_dir = str(tmp_path / "compose")
        generate(config_path="config.sample.yaml", output_dir=output_dir)

        for filename in ["compose.yaml", "traefik.yaml"]:
            with open(os.path.join(output_dir, filename)) as f:
                content = f.read()
            # The sample config uses "pass" as the password
            # It should not appear as a value in these files
            parsed = yaml.safe_load(content)
            for value in _flatten_strings(parsed):
                assert value != "pass", f"Password 'pass' leaked into {filename}"

    def test_generate_missing_config_raises(self, tmp_path):
        """Verify that a missing config file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            generate(config_path=str(tmp_path / "nonexistent.yaml"), output_dir=str(tmp_path))


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
