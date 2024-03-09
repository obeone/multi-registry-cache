from rich.prompt import Prompt, Confirm
from rich.text import Text
from ruamel.yaml import YAML
from functions import console

import tempfile

yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)
config = yaml.load(open('config.sample.yaml'))

console.print(Text("Welcome to the Traefik Registry setup", style="bold green"))
console.print()
console.print(Text("This script will help you setup a multi-registry environment", style="green"))
console.print(Text("It will ask you some questions and create a config.yaml file", style="green"))
console.print(Text("All values you enter for registries are usable in other configurations options, using interpolation like {name}", style="green"))
console.print()

config['registries'] = []
while True:
    name = Prompt.ask("[blue]Enter the name for the registry [/][italic green](e.g., docker)[/]")
    registry = {
        'name': name,
        'url': Prompt.ask(f"[blue]Enter the URL for registry {name} [/][italic green](e.g., https://docker.io)[/]"),
        'username': Prompt.ask(f"[blue]Enter the username for registry {name} [/][italic green](e.g., user)[/]"),
        'password': Prompt.ask(f"[blue]Enter the password for registry {name} [/][italic green](e.g., pass)[/]"),
        'ttl': Prompt.ask(f"[blue]Enter the TTL for registry {name} [/][italic green](e.g., '720h')[/]", default="720h")
    }
    
    if Confirm.ask(Text("Is this correct?", style="bold blue"), default=True):
        config['registries'].append(registry)
    
    if not Confirm.ask(Text("Add another registry?", style="bold blue"), default=False):
        break

domain_name = Prompt.ask("[blue]Enter the domain name to use [/][italic green](For example, {name}.registry.example.com can produce docker.registry.example.com)[/]")
config['traefik']['perRegistry']['router']['rule'] = f"Host(`{domain_name}`)"

storage_driver = Prompt.ask(Text("Choose your storage (in every case, a subdirectory per registry will be created)", style="blue"), choices=["inmemory", "filesystem", "s3", "gcs"])

storage_config = {}
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

config['registry']['baseConfig']['storage'][storage_driver] = storage_config

# Dump the YAML with comments
if Confirm.ask(Text("Is everything correct? Do we create config.yaml?", style="bold blue"), default=True):
    with open('config.yaml', 'w') as file:
        yaml.dump(config, file)

    console.print(Text("\nconfig.yaml has been created successfully!", style="green"))
else:
    with tempfile.NamedTemporaryFile('w', delete=False) as tf:
        yaml.dump(config, tf)
        temp_file_name = tf.name

    console.print(Text(f"\nconfig.yaml has not been created! The created file is in {temp_file_name}", style="bold red"))


console.print("[bold green]Now you can edit config.yaml and fine-tune parameters and when it's ok for you, just run [bold blue]'python3 generate.py'")
