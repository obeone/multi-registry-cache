import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import functions
import yaml


def test_interpolate_strings_basic():
    obj = {"a": "{var1} {var2}", "b": ["{var2}"]}
    variables = {"var1": "foo", "var2": "bar"}
    result = functions.interpolate_strings(obj, variables)
    assert result == {"a": "foo bar", "b": ["bar"]}


def test_create_registry_config_cache():
    base_config = {"proxy": {}, "redis": {}}
    registry = {
        "type": "cache",
        "url": "https://example.com",
        "username": "user",
        "password": "pass",
        "ttl": "24h",
        "name": "example",
    }
    cfg = functions.create_registry_config(base_config, registry, 2)
    assert cfg["proxy"]["remoteurl"] == "https://example.com"
    assert cfg["proxy"]["username"] == "user"
    assert cfg["proxy"]["password"] == "pass"
    assert cfg["proxy"]["ttl"] == "24h"
    assert cfg["redis"]["db"] == 2


def test_create_registry_config_registry_type_removes_proxy():
    base_config = {"proxy": {}, "redis": {}}
    registry = {"type": "registry", "name": "private"}
    cfg = functions.create_registry_config(base_config, registry, 1)
    assert "proxy" not in cfg
    assert cfg["redis"]["db"] == 1


def test_create_docker_service_interpolates_fields():
    registry = {"name": "foo"}
    custom = {"image": "registry:2", "volumes": ["./{name}.yaml:/data/{name}.yaml"]}
    result = functions.create_docker_service(registry, custom)
    assert result == {"image": "registry:2", "volumes": ["./foo.yaml:/data/foo.yaml"]}


def test_create_traefik_router_and_service(tmp_path):
    registry = {"name": "bar"}
    router_custom = {"rule": "Host(`{name}.example.com`)"}
    service_custom = {"servers": [{"url": "http://{name}:5000"}]}

    router = functions.create_traefik_router(registry, router_custom)
    service = functions.create_traefik_service(registry, service_custom)

    assert router["rule"] == "Host(`bar.example.com`)"
    assert service["servers"][0]["url"] == "http://bar:5000"


def test_write_helpers(tmp_path):
    yaml_file = tmp_path / "test.yaml"
    text_file = tmp_path / "test.txt"

    data = {"hello": "world"}
    functions.write_yaml_file(yaml_file, data)
    functions.write_to_file(text_file, "content")

    with open(yaml_file) as f:
        loaded = yaml.safe_load(f)
    with open(text_file) as f:
        txt = f.read()

    assert loaded == data
    assert txt == "content"


def test_write_http_secret_idempotent(tmp_path, monkeypatch):
    compose_dir = tmp_path / "compose"
    compose_dir.mkdir()
    monkeypatch.chdir(tmp_path)

    # First call creates the secret
    functions.write_http_secret()
    env_file = compose_dir / ".env"
    with open(env_file) as f:
        lines = f.readlines()
    assert len(lines) == 1
    assert lines[0].startswith("REGISTRY_HTTP_SECRET=")
    first_secret = lines[0]

    # Second call should not append another secret
    functions.write_http_secret()
    with open(env_file) as f:
        lines_after = f.readlines()
    assert lines_after[0] == first_secret
    assert len(lines_after) == 1
