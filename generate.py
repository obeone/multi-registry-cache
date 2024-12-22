"""
This module sets up a multi-registry environment by creating configuration files 
for Docker Compose, registry and Traefik.
See the README.md file for more information.
"""
import os
import yaml
import functions
from functions import console
from rich.text import Text


# Load config
try:
    with open('config.yaml', 'r', encoding='UTF-8') as file:
        config = yaml.safe_load(file)
        console.print(Text("Config loaded successfully", style="bold green"))
except FileNotFoundError:
    console.print(Text("Error: config.yaml not found", style="bold red"))
    raise

try:
    registries = config['registries']
    docker_config = config['docker']['baseConfig']
    docker_perregistry = config['docker']['perRegistry']
    traefik_config = config['traefik']['baseConfig']
    traefik_perregistry = config['traefik']['perRegistry']
    registry_config = config['registry']['baseConfig']
except KeyError as e:
    console.print(Text(f"Error: Missing key in config file - {e}", style="bold red"))
    raise

# Create a compose directory to store the configuration files
if not os.path.exists('compose'):
    os.mkdir('compose')
    os.mkdir('compose/acme')
    console.print(Text("Compose directory created", style="bold green"))
else:
    console.print(Text("Compose directory already exists", style="bold yellow"))

# Adding services to docker-compose and routers to traefik
count_redis_db = 0
for registry in registries:
    name = registry['name']

    # Creating registry configuration file
    try:
        registry_config_file = functions.create_registry_config(registry_config, registry, count_redis_db)
        functions.write_yaml_file(f'compose/{name}.yaml', registry_config_file)
        console.print(Text(f"Registry configuration file created for {name}", style="bold green"))
    except Exception as e:
        console.print(Text(f"Error creating registry configuration file for {name}: {e}", style="bold red"))
        raise

    # Unsset password before interpolate variables
    try:
        registry.pop('password')
    except KeyError:
        console.print(Text(f"Error: Missing 'password' key in registry configuration for {name}", style="bold red"))
        raise

    # Creating docker-compose and traefik configuration
    try:
        docker_config['services'][name] = functions.create_docker_service(registry, docker_perregistry['compose'])
        traefik_config['http']['routers'][name] = functions.create_traefik_router(registry, traefik_perregistry['router'])
        traefik_config['http']['services'][name] = functions.create_traefik_service(registry, traefik_perregistry['service'])
        console.print(Text(f"Docker-compose and traefik configuration created for {name}", style="bold green"))
    except Exception as e:
        console.print(Text(f"Error creating docker-compose and traefik configuration for {name}: {e}", style="bold red"))
        raise

    count_redis_db += 1

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
    
    
    functions.write_http_secret()
        
    console.print(Text("Configuration files written successfully", style="bold green"))
except Exception as e:
    console.print(Text(f"Error writing configuration files: {e}", style="bold red"))
    raise

