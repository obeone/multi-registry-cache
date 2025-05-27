"""
Setup script for Traefik Registry multi-registry environment configuration.

This script interactively prompts the user to configure multiple registries,
storage options, and domain settings, then generates a config.yaml file
based on the inputs.

Usage:
    Run this script and follow the prompts to create or update the configuration.

Modules used:
- rich: for enhanced console input/output
- ruamel.yaml: for YAML parsing and writing with preserved formatting
"""

from rich.prompt import Prompt, Confirm
from rich.text import Text
from ruamel.yaml import YAML
from functions import console
import os
import tempfile


def main():
    """
    Main function to run the interactive setup for Traefik Registry multi-registry environment.

    It prompts the user for registry details, storage configuration, and domain settings,
    then generates a config.yaml file based on the provided inputs.

    The configuration supports multiple registries, including private registries,
    and various storage backends such as inmemory, filesystem, S3, and GCS.

    The function uses rich for console interaction and ruamel.yaml for YAML handling.

    Returns:
        None
    """
    # Initialize the YAML parser with specific settings to preserve quotes and indentation
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)

    # Load the default configuration from a sample file
    with open('config.sample.yaml') as sample_file:
        config = yaml.load(sample_file)

    # Print welcome message using rich's console for better formatting
    console.print(Text("Welcome to the Traefik Registry setup", style="bold green"))
    console.print()
    console.print(Text("This script will help you setup a multi-registry environment", style="green"))
    console.print(Text("It will ask you some questions and create a config.yaml file", style="green"))
    console.print(Text("All values you enter for registries are usable in other configurations options, using interpolation like {name}", style="green"))
    console.print()

    # Initialize the list of registries in the configuration
    config['registries'] = []

    # Loop to collect information about each registry
    while True:
        # Prompt user for registry name with a default value
        name = Prompt.ask("[blue]Enter the name for the registry [/][italic green](e.g., docker)[/]", default="docker")

        # Collect details of the registry including URL, username, password, and TTL
        registry = {
            'name': name,
            'type': 'cache',
            'url': Prompt.ask(f"[blue]Enter the URL for registry {name} [/][italic green](e.g., https://registry-1.docker.io)[/]", default="https://registry-1.docker.io"),
            'username': Prompt.ask(f"[blue]Enter the username for registry {name} [/][italic green](e.g., user)[/]"),
            'password': Prompt.ask(f"[blue]Enter the password for registry {name} [/][italic green](e.g., pass)[/]"),
            'ttl': Prompt.ask(f"[blue]Enter the TTL for registry {name} [/][italic green](e.g., '720h')[/]", default="720h")
        }

        # Ask user to confirm if the entered information is correct
        if Confirm.ask(Text("Is this correct?", style="bold blue"), default=True):
            config['registries'].append(registry)

        # Ask if user wants to add another registry
        if not Confirm.ask(Text("Add another registry?", style="bold blue"), default=False):
            break

    # Check if user wants to add a private registry
    if Confirm.ask(Text("Do you want to add a private registry?", style="bold blue"), default=False):
        # Collect details for the private registry
        name = Prompt.ask("[blue]Enter the name for your private registry [/][italic green](e.g., private)[/]", default="private")
        private_registry = {
            'name': name,
            'type': 'registry',
        }
        config['registries'].append(private_registry)

    # Get domain name from user
    domain_name = Prompt.ask("[blue]Enter the domain name to use [/][italic green](For example, {name}.registry.example.com can produce docker.registry.example.com)[/]")
    config['traefik']['perRegistry']['router']['rule'] = f"Host(`{domain_name}`)"

    # Ask user for storage driver choice
    storage_driver = Prompt.ask(Text("Choose your storage (in every case, a subdirectory per registry will be created)", style="blue"), choices=["inmemory", "filesystem", "s3", "gcs"])

    # Initialize dictionary to hold configuration for the chosen storage driver
    storage_config = {}

    # Collect specific details based on the selected storage driver
    if storage_driver == "s3":
        storage_config = {
            'accesskey': Prompt.ask(Text("Enter the S3 access key", style="yellow")),
            'secretkey': Prompt.ask(Text("Enter the S3 secret key", style="yellow")),
            'bucket': Prompt.ask(Text("Enter the S3 bucket name", style="yellow")),
            'region': Prompt.ask(Text("Enter the S3 region", style="yellow")),
            'regionendpoint': Prompt.ask(Text("Enter the S3 region endpoint", style="yellow"), default="https://s3.amazonaws.com"),
            'rootdirectory': '{name}',
        }
    elif storage_driver == "filesystem":
        storage_config = {
            'rootdirectory': Prompt.ask(Text("Enter the root directory for filesystem storage (e.g., /var/lib/registry-cache)", style="yellow"))
        }
        storage_config['rootdirectory'] += '/{name}'

        # Ask if a bind-mount is needed
        if Confirm.ask(Text("Do you need to bind-mount this path on the host?", style="yellow"), default=True):
            config['docker']['perRegistry']['compose']['volumes'].append(f"{storage_config['rootdirectory']}:{storage_config['rootdirectory']}")

    elif storage_driver == "gcs":
        storage_config = {
            'bucket': Prompt.ask(Text("Enter the GCS bucket name", style="yellow")),
            'rootdirectory': '{name}',
            'keyfile': Prompt.ask(Text("Enter the GCS keyfile content (in JSON format)", style="yellow"))
        }
    elif storage_driver == "inmemory":
        storage_config = {}

    # Add the storage configuration to the main configuration
    config['registry']['baseConfig']['storage'][storage_driver] = storage_config

    # Ask if user wants to proceed with creating config.yaml
    if Confirm.ask(Text("Is everything correct? Do we create config.yaml?", style="bold blue"), default=True):
        # Write the final configuration to config.yaml
        with open('config.yaml', 'w') as file:
            yaml.dump(config, file)

        console.print(Text("\nconfig.yaml has been created successfully!", style="green"))
    else:
        # If not confirmed, write to a temporary file
        with tempfile.NamedTemporaryFile('w', delete=False) as tf:
            yaml.dump(config, tf)
            temp_file_name = tf.name

        console.print(Text(f"\nconfig.yaml has not been created! The created file is in {temp_file_name}", style="bold red"))

    # Determine the command to run based on whether running inside a Docker container or not
    if os.environ.get('IN_DOCKER', False):
        command = 'docker run --rm -ti -v "./config.yaml:/app/config.yaml" -v "./compose:/app/compose" obeoneorg/multi-registry-cache generate'
    else:
        command = 'python3 generate.py'

    # Print the final message with instructions for next steps
    console.print(f"[bold green]Now you can edit [bold blue]config.yaml[bold green] and fine-tune parameters and when it's ok for you, just run :\n[bold blue]{command}")


if __name__ == "__main__":
    main()
