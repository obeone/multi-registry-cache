"""Shared fixtures for multi-registry-cache tests."""

import copy

import pytest
import yaml


@pytest.fixture
def sample_config():
    """Load and return the sample configuration as a dict."""
    with open("config.sample.yaml", "r", encoding="UTF-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def cache_registry():
    """Return a sample cache-type registry dict."""
    return {
        "name": "dockerhub",
        "type": "cache",
        "url": "https://registry-1.docker.io",
        "username": "testuser",
        "password": "testpass",
        "ttl": "720h",
    }


@pytest.fixture
def private_registry():
    """Return a sample private (non-cache) registry dict."""
    return {
        "name": "private",
        "type": "registry",
    }


@pytest.fixture
def base_registry_config(sample_config):
    """Return a deep copy of the base registry config from the sample."""
    return copy.deepcopy(sample_config["registry"]["baseConfig"])
