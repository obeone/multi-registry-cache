"""
This module sets up a multi-registry environment by creating configuration files
for Docker Compose, registry, and Traefik.
See the README.md file for more information.

Usage:
    Run this script to generate configuration files based on the config.yaml.
"""
import os
import re
import yaml
import functions
from functions import console
from rich.text import Text
import copy


def parse_duration_to_seconds(duration):
    '''

    Convert a duration string expressed with unit suffixes into seconds.

    Args:
        duration (str): The duration string to parse (for example "12h" or "30m").

    Returns:
        int: The computed duration in seconds.

    '''

    if not isinstance(duration, str):
        raise ValueError('Duration must be provided as a string')

    pattern = re.compile(r'(\d+)([smhdSMHD])')
    total_seconds = 0
    index = 0
    duration = duration.strip()

    for match in pattern.finditer(duration):
        if match.start() != index:
            raise ValueError('Invalid duration format')
        value = int(match.group(1))
        unit = match.group(2).lower()
        if unit == 's':
            total_seconds += value
        elif unit == 'm':
            total_seconds += value * 60
        elif unit == 'h':
            total_seconds += value * 3600
        elif unit == 'd':
            total_seconds += value * 86400
        else:
            raise ValueError('Unsupported duration unit')
        index = match.end()

    if index != len(duration) or total_seconds == 0:
        raise ValueError('Invalid duration format')

    return total_seconds


def build_garbage_collect_command(cron_expression=None, interval_seconds=None):
    '''

    Create the shell command that triggers registry garbage collection.

    Args:
        cron_expression (str, optional): Cron expression to schedule the command.
        interval_seconds (int, optional): Interval in seconds for the sleep loop.

    Returns:
        list: A list representing the command to execute in Docker Compose.

    '''

    base_command = 'registry garbage-collect --delete-untagged /etc/docker/registry/config.yml'

    if cron_expression:
        cron_entry = f"{cron_expression} {base_command}"
        escaped_entry = cron_entry.replace('"', '\\"')
        shell_command = (
            "printf '%s\\n' \""
            + escaped_entry
            + "\" > /etc/crontabs/root && crond -f -l 8 -L /dev/stdout"
        )
        return ['sh', '-c', shell_command]

    if interval_seconds:
        shell_command = (
            f"while true; do {base_command}; sleep {interval_seconds}; done"
        )
        return ['sh', '-c', shell_command]

    raise ValueError('A cron expression or interval must be provided for garbage collection')


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

    try:
        garbage_collect = registry.get('garbageCollect')
        if garbage_collect:
            cron_expression = None
            interval_seconds = None

            if isinstance(garbage_collect, dict):
                cron_expression = garbage_collect.get('cron')
                interval_value = garbage_collect.get('interval')
                if interval_value is not None:
                    interval_seconds = parse_duration_to_seconds(interval_value)
            elif isinstance(garbage_collect, str):
                stripped_value = garbage_collect.strip()
                if len(stripped_value.split()) >= 5:
                    cron_expression = stripped_value
                else:
                    interval_seconds = parse_duration_to_seconds(stripped_value)
            else:
                raise ValueError('garbageCollect must be a string or a mapping')

            if cron_expression and interval_seconds:
                raise ValueError('Specify either cron or interval for garbageCollect, not both')

            if cron_expression:
                cron_expression = cron_expression.strip()
                if len(cron_expression.split()) < 5:
                    raise ValueError('Invalid cron expression for garbageCollect')

            if not cron_expression and not interval_seconds:
                raise ValueError('garbageCollect configuration is incomplete')

            gc_service_name = f"registry-gc-{name}"
            gc_service = copy.deepcopy(docker_config['services'][name])
            gc_service.pop('ports', None)
            gc_service.pop('container_name', None)
            if 'depends_on' in gc_service:
                depends_on = gc_service['depends_on']
                if isinstance(depends_on, list):
                    gc_service['depends_on'] = [dep for dep in depends_on if dep != name]
                elif isinstance(depends_on, dict):
                    depends_on.pop(name, None)
            gc_service['restart'] = gc_service.get('restart', 'always')
            gc_service['command'] = build_garbage_collect_command(
                cron_expression=cron_expression,
                interval_seconds=interval_seconds,
            )
            docker_config['services'][gc_service_name] = gc_service
            console.print(Text(f"Garbage collection service configured for {name}", style="bold green"))
    except Exception as e:
        console.print(Text(f"Error configuring garbage collection for {name}: {e}", style="bold red"))
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

