#!/usr/bin/env python3
"""
Utilities for cleaning up expired repositories from cache registries.
"""

import argparse
import copy
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import yaml
from rich.console import Console
from rich.text import Text

# Ensure the repository root is available for imports when executed directly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import functions  # noqa: E402  pylint: disable=wrong-import-position

console = Console()
_DURATION_PATTERN = re.compile(r"(?P<value>\d+(?:\.\d+)?)(?P<unit>[smhdw])")
_DURATION_UNIT_SECONDS = {
    's': 1,
    'm': 60,
    'h': 3600,
    'd': 86400,
    'w': 604800,
}


def load_yaml_file(path: str) -> dict:
    '''
    Load a YAML file from disk.

    Args:
        path (str): The path to the YAML file.

    Returns:
        dict: The parsed YAML content.

    '''
    with open(path, 'r', encoding='utf-8') as handle:
        return yaml.safe_load(handle) or {}


def parse_duration_to_seconds(value) -> int:
    '''
    Convert a TTL duration expressed as a string or number into seconds.

    Args:
        value (str or int or float): Duration value in a Go-like format such as "720h" or a numeric value representing seconds.

    Returns:
        int: The duration in seconds.

    '''
    if value is None:
        raise ValueError('Duration cannot be None.')

    if isinstance(value, (int, float)):
        if value < 0:
            raise ValueError('Duration cannot be negative.')
        return int(value)

    text_value = str(value).strip()
    if text_value.isdigit():
        return int(text_value)

    total_seconds = 0.0
    position = 0
    for match in _DURATION_PATTERN.finditer(text_value):
        if match.start() != position:
            raise ValueError(f'Unsupported duration format: {text_value}')
        number = float(match.group('value'))
        unit = match.group('unit')
        total_seconds += number * _DURATION_UNIT_SECONDS[unit]
        position = match.end()

    if position != len(text_value):
        raise ValueError(f'Unsupported duration format: {text_value}')

    return int(total_seconds)


def extract_storage_metadata(registry_config: dict) -> Tuple[Optional[str], Optional[str]]:
    '''
    Extract storage driver and location information from a registry configuration.

    Args:
        registry_config (dict): The rendered registry configuration.

    Returns:
        tuple: A tuple with the storage driver name and the storage path or identifier.

    '''
    if not isinstance(registry_config, dict):
        return None, None

    storage_config = registry_config.get('storage', {})
    if not isinstance(storage_config, dict):
        return None, None

    filesystem_config = storage_config.get('filesystem')
    if isinstance(filesystem_config, dict):
        root_directory = filesystem_config.get('rootdirectory')
        if root_directory:
            return 'filesystem', root_directory

    s3_config = storage_config.get('s3')
    if isinstance(s3_config, dict):
        bucket = s3_config.get('bucket')
        root_directory = s3_config.get('rootdirectory', '')
        if bucket:
            location = f"s3://{bucket}/{root_directory}" if root_directory else f"s3://{bucket}"
            return 's3', location

    return None, None


def build_entry_from_registry(registry: dict, registry_config: dict) -> Optional[dict]:
    '''
    Build a cleanup schedule entry based on the rendered registry configuration.

    Args:
        registry (dict): Registry definition from config.yaml.
        registry_config (dict): Rendered registry configuration.

    Returns:
        dict or None: Cleanup entry data or None when no TTL or storage information is available.

    '''
    ttl_value = registry.get('ttl')
    registry_type = registry.get('type', 'cache')
    if not ttl_value or registry_type != 'cache':
        return None

    storage_driver, storage_path = extract_storage_metadata(registry_config)
    if not storage_path:
        return None

    return {
        'name': registry.get('name'),
        'ttl': str(ttl_value),
        'type': registry_type,
        'storage_driver': storage_driver,
        'storage_path': storage_path,
    }


def build_schedule_from_config(config_path: str) -> List[dict]:
    '''
    Generate a cleanup schedule directly from the configuration file.

    Args:
        config_path (str): Path to config.yaml.

    Returns:
        list: A list of cleanup schedule entries.

    '''
    config_data = load_yaml_file(config_path)
    registries = config_data.get('registries', [])
    registry_base = config_data.get('registry', {}).get('baseConfig', {})

    schedule: List[dict] = []
    redis_db = 0
    for item in registries:
        registry_definition = copy.deepcopy(item)
        if 'type' not in registry_definition:
            registry_definition['type'] = 'cache'
        registry_config = copy.deepcopy(registry_base)
        rendered_config = functions.create_registry_config(registry_config, registry_definition, redis_db)
        redis_db += 1
        entry = build_entry_from_registry(registry_definition, rendered_config)
        if entry:
            schedule.append(entry)

    return schedule


def load_schedule(schedule_path: str) -> List[dict]:
    '''
    Load a cleanup schedule from a YAML file.

    Args:
        schedule_path (str): Path to the schedule file.

    Returns:
        list: Loaded cleanup schedule entries.

    '''
    if not schedule_path or not os.path.exists(schedule_path):
        return []

    raw_data = load_yaml_file(schedule_path)
    if isinstance(raw_data, dict):
        registries = raw_data.get('registries', [])
    elif isinstance(raw_data, list):
        registries = raw_data
    else:
        registries = []

    schedule: List[dict] = []
    for entry in registries:
        if not isinstance(entry, dict):
            continue
        normalized = {
            'name': entry.get('name'),
            'ttl': entry.get('ttl'),
            'type': entry.get('type', 'cache'),
            'storage_driver': entry.get('storage_driver'),
            'storage_path': entry.get('storage_path') or entry.get('storage'),
        }
        schedule.append(normalized)
    return schedule


def expand_storage_path(path_value: str) -> str:
    '''
    Expand environment variables and user references in a storage path value.

    Args:
        path_value (str): The path to expand.

    Returns:
        str: The expanded path string.

    '''
    return os.path.expandvars(os.path.expanduser(path_value))


def discover_repository_roots(storage_root: str) -> List[str]:
    '''
    Find repository directories stored under a registry filesystem backend.

    Args:
        storage_root (str): Path to the storage root directory.

    Returns:
        list: Repository directory paths.

    '''
    repositories_root = Path(storage_root) / 'docker/registry/v2/repositories'
    if not repositories_root.is_dir():
        return []

    repository_paths: List[str] = []
    for current_root, dirs, _files in os.walk(repositories_root):
        if '_manifests' in dirs and '_layers' in dirs:
            repository_paths.append(str(Path(current_root)))
            dirs[:] = []
    return repository_paths


def compute_repository_activity(repository_path: str) -> float:
    '''
    Compute the most recent modification time within a repository directory.

    Args:
        repository_path (str): The repository directory path.

    Returns:
        float: The latest modification time as a UNIX timestamp.

    '''
    latest = os.path.getmtime(repository_path)
    for root, dirs, files in os.walk(repository_path):
        for directory in dirs:
            try:
                latest = max(latest, os.path.getmtime(os.path.join(root, directory)))
            except FileNotFoundError:
                continue
        for file_name in files:
            file_path = os.path.join(root, file_name)
            try:
                latest = max(latest, os.path.getmtime(file_path))
            except FileNotFoundError:
                continue
    return latest


def delete_repository(repository_path: str) -> None:
    '''
    Remove a repository directory from the filesystem backend.

    Args:
        repository_path (str): The repository directory path.

    Returns:
        None

    '''
    shutil.rmtree(repository_path)


def cleanup_registry(entry: dict, dry_run: bool, reference_time: float) -> Dict[str, int]:
    '''
    Clean up repositories for a single registry entry.

    Args:
        entry (dict): Cleanup schedule entry.
        dry_run (bool): Whether to skip actual deletions.
        reference_time (float): Current UNIX timestamp.

    Returns:
        dict: Summary containing deleted and skipped counts.

    '''
    name = entry.get('name')
    ttl_value = entry.get('ttl')
    storage_driver = entry.get('storage_driver')
    storage_path = entry.get('storage_path')

    if not name or not ttl_value:
        console.print(Text('Skipping entry with missing name or TTL.', style='yellow'))
        return {'deleted': 0, 'skipped': 0}

    if storage_driver != 'filesystem':
        console.print(Text(f'Skipping registry {name}: unsupported storage driver {storage_driver}.', style='yellow'))
        return {'deleted': 0, 'skipped': 0}

    if not storage_path:
        console.print(Text(f'Skipping registry {name}: storage path is not defined.', style='yellow'))
        return {'deleted': 0, 'skipped': 0}

    try:
        ttl_seconds = parse_duration_to_seconds(ttl_value)
    except ValueError as error:
        console.print(Text(f'Skipping registry {name}: {error}', style='red'))
        return {'deleted': 0, 'skipped': 0}

    expanded_storage = expand_storage_path(storage_path)
    repository_roots = discover_repository_roots(expanded_storage)
    if not repository_roots:
        console.print(Text(f'No repositories found for registry {name} at {expanded_storage}.', style='cyan'))
        return {'deleted': 0, 'skipped': 0}

    deadline = reference_time - ttl_seconds
    deleted = 0
    skipped = 0

    for repository in repository_roots:
        try:
            last_activity = compute_repository_activity(repository)
        except FileNotFoundError:
            console.print(Text(f'Repository disappeared while scanning: {repository}', style='yellow'))
            skipped += 1
            continue

        if last_activity >= deadline:
            skipped += 1
            continue

        if dry_run:
            console.print(Text(f'[DRY-RUN] Would delete repository {repository}', style='blue'))
        else:
            delete_repository(repository)
            console.print(Text(f'Deleted repository {repository}', style='green'))
        deleted += 1

    console.print(Text(f'Registry {name}: {deleted} deleted, {skipped} retained.', style='bold magenta'))
    return {'deleted': deleted, 'skipped': skipped}


def summarize_results(results: Iterable[Dict[str, int]]) -> Dict[str, int]:
    '''
    Aggregate cleanup results from multiple registries.

    Args:
        results (Iterable[dict]): Iterable of per-registry summaries.

    Returns:
        dict: Aggregated deleted and skipped counters.

    '''
    summary = {'deleted': 0, 'skipped': 0}
    for item in results:
        summary['deleted'] += item.get('deleted', 0)
        summary['skipped'] += item.get('skipped', 0)
    return summary


def parse_arguments() -> argparse.Namespace:
    '''
    Parse command-line arguments for the cleanup helper.

    Returns:
        argparse.Namespace: Parsed arguments.

    '''
    parser = argparse.ArgumentParser(description='Clean up expired cache repositories based on TTL settings.')
    parser.add_argument('--config', default='config.yaml', help='Path to config.yaml for fallback schedule generation.')
    parser.add_argument('--schedule', default='compose/cleanup_schedule.yaml', help='Path to the generated cleanup schedule file.')
    parser.add_argument('--registry', action='append', help='Restrict cleanup to the provided registry name. Can be specified multiple times.')
    parser.add_argument('--dry-run', action='store_true', help='Print actions without deleting any data.')
    return parser.parse_args()


def main() -> None:
    '''
    Execute the cleanup workflow.

    Returns:
        None

    '''
    args = parse_arguments()
    schedule = load_schedule(args.schedule)
    if not schedule:
        console.print(Text('No cleanup schedule file found or file is empty. Falling back to config.yaml parsing.', style='yellow'))
        try:
            schedule = build_schedule_from_config(args.config)
        except FileNotFoundError:
            console.print(Text('Unable to load config.yaml for schedule generation.', style='red'))
            return

    if not schedule:
        console.print(Text('No registries with TTL configuration were found. Nothing to clean.', style='cyan'))
        return

    if args.registry:
        allowed = set(args.registry)
        schedule = [entry for entry in schedule if entry.get('name') in allowed]
        if not schedule:
            console.print(Text('No matching registries found for the provided filters.', style='yellow'))
            return

    console.print(Text('Starting cleanup operation', style='bold green'))
    reference_time = time.time()
    results = []
    for entry in schedule:
        result = cleanup_registry(entry, args.dry_run, reference_time)
        results.append(result)

    totals = summarize_results(results)
    console.print(Text(f"Cleanup finished at {datetime.now(timezone.utc).isoformat()} (UTC)", style='bold green'))
    console.print(Text(f"Total repositories deleted: {totals['deleted']}", style='bold green'))
    console.print(Text(f"Total repositories retained: {totals['skipped']}", style='bold green'))


if __name__ == '__main__':
    main()
