"""
Shared utility functions for the multi-registry cache configuration generator.

This module provides all functions needed to set up a multi-registry environment by creating
configuration files for Docker Compose, Registry and Traefik.
"""

import os
import secrets

import yaml
from rich.console import Console
from rich.text import Text

console = Console()


def interpolate_strings(obj, variables):
    """
    Recursively interpolate variables into a dictionary, list, or string.

    Parameters
    ----------
    obj : dict or list or str
        The object to interpolate.
    variables : dict
        A dictionary of variables to substitute using Python's str.format_map.

    Returns
    -------
    dict or list or str
        The interpolated object, with all {key} placeholders replaced.
    """
    if isinstance(obj, str):
        return obj.format_map(variables)
    elif isinstance(obj, dict):
        return {k: interpolate_strings(v, variables) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [interpolate_strings(elem, variables) for elem in obj]
    else:
        return obj


def create_docker_service(registry, custom=None):
    """
    Create a Docker Compose service definition for a registry.

    Parameters
    ----------
    registry : dict
        A dictionary containing the registry information (name, url, etc.).
    custom : dict, optional
        A dictionary of customizations to apply to the docker service.

    Returns
    -------
    dict
        The interpolated docker service definition.
    """
    if custom is None:
        custom = {}

    obj = {}
    obj.update(custom)

    console.print(Text("Docker service created for the registry", style="green"))
    return interpolate_strings(obj, registry)


def create_traefik_router(registry, custom=None):
    """
    Create a Traefik router object for a given registry.

    Parameters
    ----------
    registry : dict
        A dictionary containing the registry information.
    custom : dict, optional
        A dictionary of custom router properties.

    Returns
    -------
    dict
        The interpolated Traefik router definition.
    """
    if custom is None:
        custom = {}

    obj = {}
    obj.update(custom)

    console.print(Text("Traefik router object created", style="green"))
    return interpolate_strings(obj, registry)


def create_traefik_service(registry, custom=None):
    """
    Create a Traefik service object with a load balancer pointing to the registry.

    Parameters
    ----------
    registry : dict
        A dictionary containing the registry information.
    custom : dict, optional
        A dictionary of custom configuration options.

    Returns
    -------
    dict
        The interpolated Traefik service definition.
    """
    if custom is None:
        custom = {}

    obj = {}
    obj.update(custom)

    console.print(Text("Traefik service object created", style="green"))
    return interpolate_strings(obj, registry)


def create_registry_config(config, registry, db):
    """
    Create a registry configuration by merging base config with registry-specific values.

    For cache-type registries, sets the proxy remote URL, credentials, and TTL.
    For regular registries, removes the proxy block entirely.
    Assigns an auto-incrementing Redis database number.

    Parameters
    ----------
    config : dict
        The base registry configuration to update (will be mutated).
    registry : dict
        The registry information (name, type, url, username, password, ttl).
    db : int
        The Redis database number to assign to this registry.

    Returns
    -------
    dict
        The fully interpolated registry configuration.
    """
    if registry['type'] == 'cache':
        config['proxy']['remoteurl'] = registry['url']
        if 'username' in registry and 'password' in registry:
            config['proxy']['username'] = registry['username']
            config['proxy']['password'] = registry['password']
        if 'ttl' in registry:
            config['proxy']['ttl'] = registry['ttl']
    elif 'proxy' in config:
        del config['proxy']

    interpolated = interpolate_strings(config, registry)

    if isinstance(interpolated, dict) and 'redis' in interpolated:
        redis_config = interpolated.get('redis')
        if isinstance(redis_config, dict):
            redis_config['db'] = int(db)

    console.print(Text("Registry configuration created", style="green"))
    return interpolated


def write_yaml_file(filename, data):
    """
    Write data to a YAML file.

    Parameters
    ----------
    filename : str
        The path of the file to write to.
    data : dict
        The data to serialize as YAML.
    """
    with open(filename, 'w', encoding='UTF-8') as file:
        yaml.dump(data, file)
    console.print(Text(f"Data written to {filename}", style="green"))


def write_to_file(filename, data):
    """
    Write plain text data to a file.

    Parameters
    ----------
    filename : str
        The path of the file to write to.
    data : str
        The text content to write.
    """
    with open(filename, 'w', encoding='UTF-8') as file:
        file.write(data)
    console.print(Text(f"Data written to {filename}", style="green"))


def write_http_secret(output_dir="compose"):
    """
    Write a random HTTP secret to the .env file if not already present.

    Generates a 32-byte hex token for REGISTRY_HTTP_SECRET and appends it
    to the .env file in the output directory.

    Parameters
    ----------
    output_dir : str
        The directory containing the .env file. Defaults to "compose".
    """
    env_path = os.path.join(output_dir, '.env')
    if not os.path.exists(env_path) or 'REGISTRY_HTTP_SECRET' not in open(env_path).read():
        with open(env_path, 'a') as env_file:
            env_file.write(f"REGISTRY_HTTP_SECRET={secrets.token_hex(32)}\n")
        console.print(Text("HTTP secret written to .env file", style="green"))
    else:
        console.print(Text(f"{env_path} already exists or REGISTRY_HTTP_SECRET is already set", style="yellow"))
