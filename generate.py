"""
This module sets up a multi-registry environment by creating configuration files
for Docker Compose, registry, and Traefik.
See the README.md file for more information.

Usage:
    Run this script to generate configuration files based on the config.yaml.
"""
import os
import yaml
import functions
from functions import console
from rich.text import Text
import copy


# Load configuration from config.yaml file
try:
    with open('config.yaml', 'r', encoding='UTF-8') as file:
        base_config = yaml.safe_load(file)
        console.print(Text("Config loaded successfully", style="bold green"))
except FileNotFoundError:
    console.print(Text("Error: config.yaml not found", style="bold red"))
    raise

# Extract configuration sections from the loaded config
try:
    registries = base_config['registries']
    docker_config = base_config['docker']['baseConfig']
    docker_perregistry = base_config['docker']['perRegistry']
    traefik_config = base_config['traefik']['baseConfig']
    traefik_perregistry = base_config['traefik']['perRegistry']
    registry_config = base_config['registry']['baseConfig']
except KeyError as e:
    console.print(Text(f"Error: Missing key in config file - {e}", style="bold red"))
    raise

# Create a compose directory to store the configuration files if it does not exist
if not os.path.exists('compose'):
    os.mkdir('compose')
    os.mkdir('compose/acme')
    console.print(Text("Compose directory created", style="bold green"))
else:
    console.print(Text("Compose directory already exists", style="bold yellow"))

# Initialize Redis database count for registries
count_redis_db = 0

# Iterate over each registry to create configuration files and update docker and traefik configs
for registry in registries:
    name = registry['name']

    # Create registry configuration file
    try:
        # Retrocompatibility with old config files without 'type' field
        if 'type' not in registry:
            registry['type'] = 'cache'
            console.print(Text(f"No type specified for registry {name}, defaulting to cache", style="bold yellow"))

        # Deep copy base registry config and create specific config for this registry
        registry_config_copy = copy.deepcopy(registry_config)
        registry_config_file = functions.create_registry_config(registry_config_copy, registry, count_redis_db)
        functions.write_yaml_file(f'compose/{name}.yaml', registry_config_file)
        console.print(Text(f"Registry configuration file created for {name}", style="bold green"))
    except Exception as e:
        console.print(Text(f"Error creating registry configuration file for {name}: {e}", style="bold red"))
        raise

    # Unset password before interpolating variables to avoid leaking sensitive data
    try:
        if 'password' in registry:
            registry.pop('password')
    except KeyError:
        console.print(Text(f"Error: Missing 'password' key in registry configuration for {name}", style="bold red"))
        raise

    # Create docker-compose and traefik configuration entries for this registry
    try:
        docker_config['services'][name] = functions.create_docker_service(registry, docker_perregistry['compose'])
        traefik_config['http']['routers'][name] = functions.create_traefik_router(registry, traefik_perregistry['router'])
        traefik_config['http']['services'][name] = functions.create_traefik_service(registry, traefik_perregistry['service'])
        console.print(Text(f"Docker-compose and traefik configuration created for {name}", style="bold green"))
    except Exception as e:
        console.print(Text(f"Error creating docker-compose and traefik configuration for {name}: {e}", style="bold red"))
        raise

    # Increment Redis database count for next registry
    count_redis_db += 1

# Write final configuration files and handle deprecated docker-compose.yml file
try:
    functions.write_yaml_file('compose/compose.yaml', docker_config)
    functions.write_yaml_file('compose/traefik.yaml', traefik_config)
    functions.write_to_file('compose/redis.conf', f'databases {count_redis_db}')

    # If docker-compose.yml exists, ask for confirmation before removing it
    docker_compose_path = 'compose/docker-compose.yml'
    if os.path.exists(docker_compose_path):
        console.print(Text("docker-compose.yml file exists, and now we use `compose.yaml` filename. Do you want to remove the deprecated `docker-compose.yml` file? (Y/n): ", style="bold yellow"), end="")
        user_input = input().strip().lower()
        if user_input == "" or user_input == 'y':
            os.remove(docker_compose_path)
            console.print(Text("Existing docker-compose.yml file removed", style="bold blue"))
        else:
            console.print(Text("docker-compose.yml file not removed", style="bold yellow"))

    # Write HTTP secret file
    functions.write_http_secret()

    console.print(Text("Configuration files written successfully", style="bold green"))
except Exception as e:
    console.print(Text(f"Error writing configuration files: {e}", style="bold red"))
    raise

