"""
CLI entry point for the multi-registry cache configuration generator.

Provides two subcommands:
- setup: Interactive wizard to create a config.yaml
- generate: Generate Docker Compose, Traefik, and registry config files
"""

import sys

import typer

app = typer.Typer(
    name="multi-registry-cache",
    no_args_is_help=True,
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Generate Docker Compose, Traefik, and registry configuration files for multi-registry pull-through caches.",
)

_ZSH_COMPLETION = """\
#compdef multi-registry-cache

_multi-registry-cache() {
    local -a commands
    commands=(
        'setup:Interactive wizard to create a config.yaml file'
        'generate:Generate Docker Compose, Traefik, and registry config files'
        'completion:Print shell completion script'
    )

    _arguments -C \\
        '1:command:->cmd' \\
        '*::arg:->args'

    case "$state" in
        cmd)
            _describe 'command' commands
            ;;
        args)
            case "$words[1]" in
                setup)
                    _arguments \\
                        '(-c --config)'{-c,--config}'[Output config file path]:path:_files' \\
                        '(-h --help)'{-h,--help}'[Show help]'
                    ;;
                generate)
                    _arguments \\
                        '(-c --config)'{-c,--config}'[Config file path]:path:_files' \\
                        '(-o --output-dir)'{-o,--output-dir}'[Output directory]:dir:_directories' \\
                        '(-h --help)'{-h,--help}'[Show help]'
                    ;;
                completion)
                    _arguments \\
                        '1:shell:(zsh bash fish)'
                    ;;
            esac
            ;;
    esac
}

_multi-registry-cache "$@"
"""

_BASH_COMPLETION = """\
_multi_registry_cache() {
    local cur prev commands
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    commands="setup generate completion"

    if [[ ${COMP_CWORD} -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "${commands}" -- "${cur}") )
        return 0
    fi

    case "${COMP_WORDS[1]}" in
        setup)
            COMPREPLY=( $(compgen -W "--config -c --help -h" -- "${cur}") )
            ;;
        generate)
            COMPREPLY=( $(compgen -W "--config -c --output-dir -o --help -h" -- "${cur}") )
            ;;
        completion)
            COMPREPLY=( $(compgen -W "zsh bash fish" -- "${cur}") )
            ;;
    esac
}

complete -F _multi_registry_cache multi-registry-cache
"""

_FISH_COMPLETION = """\
complete -c multi-registry-cache -f
complete -c multi-registry-cache -n '__fish_use_subcommand' -a setup -d 'Interactive wizard to create a config.yaml file'
complete -c multi-registry-cache -n '__fish_use_subcommand' -a generate -d 'Generate Docker Compose, Traefik, and registry config files'
complete -c multi-registry-cache -n '__fish_use_subcommand' -a completion -d 'Print shell completion script'
complete -c multi-registry-cache -n '__fish_seen_subcommand_from setup' -s c -l config -d 'Output config file path' -r
complete -c multi-registry-cache -n '__fish_seen_subcommand_from generate' -s c -l config -d 'Config file path' -r
complete -c multi-registry-cache -n '__fish_seen_subcommand_from generate' -s o -l output-dir -d 'Output directory' -r -a '(__fish_complete_directories)'
complete -c multi-registry-cache -n '__fish_seen_subcommand_from completion' -a 'zsh bash fish'
"""

_COMPLETIONS = {
    "zsh": _ZSH_COMPLETION,
    "bash": _BASH_COMPLETION,
    "fish": _FISH_COMPLETION,
}


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


@app.command()
def completion(
    shell: str = typer.Argument(None, help="Shell type: zsh, bash, or fish"),
):
    """Print shell completion script (static, no runtime overhead)."""
    if shell is None:
        # Auto-detect from parent process or SHELL env
        import os
        shell_env = os.environ.get("SHELL", "")
        if "zsh" in shell_env:
            shell = "zsh"
        elif "fish" in shell_env:
            shell = "fish"
        else:
            shell = "bash"

    script = _COMPLETIONS.get(shell)
    if script is None:
        print(f"Unknown shell: {shell}. Supported: zsh, bash, fish", file=sys.stderr)
        raise SystemExit(1)

    print(script)
