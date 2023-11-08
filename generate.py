"""
This module sets up a multi-registry environment by creating configuration files 
for Docker Compose, registry and Traefik.
See the README.md file for more information.
"""

import os
import yaml
import functions

# Load config
with open('config.yaml', 'r', encoding='UTF-8') as file:
    config = yaml.safe_load(file)

    registries = config['registries']

    docker_config = config['docker']['baseConfig']
    docker_perregistry = config['docker']['perRegistry']
    traefik_config = config['traefik']['baseConfig']
    traefik_perregistry = config['traefik']['perRegistry']
    registry_config = config['registry']['baseConfig']


# Create a compose directory to store the configuration files
if not os.path.exists('compose'):
    os.mkdir('compose')
    os.mkdir('compose/acme')

# Adding services to docker-compose and routers to traefik
count_redis_db = 0
for registry in registries:
    name = registry['name']

    # Creating registry configuration file
    registry_config_file = functions.create_registry_config(registry_config, registry, count_redis_db)
    functions.write_yaml_file(f'compose/{name}.yaml', registry_config_file)

    # Unsset password before interpolate variables
    registry.pop('password')

    # Creating docker-compose and traefik configuration
    docker_config['services'][name] = functions.create_docker_service(registry, docker_perregistry['compose'])
    traefik_config['http']['routers'][name] = functions.create_traefik_router(registry, traefik_perregistry['router'])
    traefik_config['http']['services'][name] = functions.create_traefik_service(registry, traefik_perregistry['service'])

    count_redis_db += 1


# Writing configuration files
functions.write_yaml_file('compose/docker-compose.yml', docker_config)
functions.write_yaml_file('compose/traefik.yaml', traefik_config)
functions.write_to_file('compose/redis.conf', f'databases {count_redis_db}')
