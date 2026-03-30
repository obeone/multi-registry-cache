"""
CLI entry point for the multi-registry cache configuration generator.

Provides two subcommands:
- setup: Interactive wizard to create a config.yaml
- generate: Generate Docker Compose, Traefik, and registry config files
"""

import typer

app = typer.Typer(
    name="multi-registry-cache",
    no_args_is_help=True,
    help="Generate Docker Compose, Traefik, and registry configuration files for multi-registry pull-through caches.",
)


@app.command()
def setup(
    config: str = typer.Option("config.yaml", "--config", "-c", help="Output config file path"),
):
    """Interactive wizard to create a config.yaml file."""
    from multi_registry_cache.setup_wizard import main

    main(config_path=config)


@app.command()
def generate(
    config: str = typer.Option("config.yaml", "--config", "-c", help="Config file path"),
    output_dir: str = typer.Option("compose", "--output-dir", "-o", help="Output directory for generated files"),
):
    """Generate Docker Compose, Traefik, and registry config files from a config.yaml."""
    from multi_registry_cache.generate import generate as run_generate

    run_generate(config_path=config, output_dir=output_dir)
