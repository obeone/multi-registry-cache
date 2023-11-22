"""
This module provides all functions needed to set up a multi-registry environment by creating
configuration files for Docker Compose, Registry and Traefik.
"""

import yaml

def interpolate_strings(obj, variables):
    """
    Recursively interpolates variables into a dictionary or list of strings.

    Args:
        obj (dict or list or str): The object to interpolate.
        variables (dict): A dictionary of variables to interpolate.

    Returns:
        The interpolated object.
    """
    if isinstance(obj, str):
        # If the object is a string, interpolate the variables into it.
        return obj.format_map(variables)
    elif isinstance(obj, dict):
        # If the object is a dictionary, interpolate the variables into each value.
        return {k: interpolate_strings(v, variables) for k, v in obj.items()}
    elif isinstance(obj, list):
        # If the object is a list, interpolate the variables into each element.
        return [interpolate_strings(elem, variables) for elem in obj]
    else:
        # If the object is not a string, dictionary, or list, return it unchanged.
        return obj


def create_docker_service(registry, custom={}):
    """Creates a docker service for the registry.
    
    Args:
        registry (dict): A dictionary containing the registry information.
        custom (dict): A dictionary of customizations to apply to the 
            docker service.
    Returns:
        dict: The docker service.
    """
    obj = {
    }
    obj.update(custom)
    
    return interpolate_strings(obj, registry)


def create_traefik_router(registry, custom={}):
    """
    Creates a Traefik router object for a given registry.

    Args:
        registry (str): The name of the registry.
        custom (dict, optional): A dictionary of custom router properties. Defaults to {}.

    Returns:
        dict: A dictionary representing the Traefik router object.
    """
    obj = {
    }
    
    obj.update(custom)
    
    return interpolate_strings(obj, registry)

def create_traefik_service(registry, custom={}):
    """
    Creates a Traefik service object with a load balancer configuration that points to the specified registry.

    Args:
        registry (str): The URL of the registry to point the load balancer to.
        custom (dict, optional): A dictionary of custom configuration options to add to the service object. Defaults to {}.

    Returns:
        dict: A Traefik service object with the specified load balancer configuration.
    """
    obj = {
    }
    obj.update(custom)
    
    return interpolate_strings(obj, registry)


def create_registry_config(config, registry, db):
    """
    Creates a registry configuration by updating the given configuration with the registry's information.

    Args:
        config (dict): The configuration to update.
        registry (dict): The registry information to use for the update.
        db: The database to associate with the registry.

    Returns:
        dict: The updated configuration.
    """
    config['proxy']['remoteurl'] = registry['url']
    if registry['username'] and registry['password']:
        config['proxy']['username'] = registry['username']
        config['proxy']['password'] = registry['password']
    if registry['ttl']:
        config['proxy']['ttl'] = registry['ttl']

    interpolated = interpolate_strings(config, registry)
    
    if interpolated['redis']:
        interpolated['redis']['db'] = int(db)
        
    return interpolated


def write_yaml_file(filename, data):
    """
    Write data to a YAML file.

    Args:
        filename (str): The name of the file to write to.
        data (dict): The data to write to the file.
    """
    with open(filename, 'w', encoding='UTF-8') as file:
        yaml.dump(data, file)



def write_to_file(filename, data):
    """
    Write data to a file.

    Args:
        filename (str): The name of the file to write to.
        data (str): The data to write to the file.
    """
    with open(filename, 'w', encoding='UTF-8') as file:
        file.write(data)
