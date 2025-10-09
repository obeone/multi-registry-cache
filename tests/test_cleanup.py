"""Tests for the maintenance cleanup helper."""

import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from maintenance import cleanup


def test_parse_duration_to_seconds_handles_composite_values():
    """
    Ensure the duration parser supports composite values with multiple units.
    """
    assert cleanup.parse_duration_to_seconds('1h30m') == 5400


def test_parse_duration_to_seconds_accepts_numeric_values():
    """
    Ensure numeric TTL values are interpreted as seconds without modification.
    """
    assert cleanup.parse_duration_to_seconds(120) == 120


def test_build_schedule_from_config_generates_storage_paths(tmp_path):
    """
    Validate that schedule generation extracts the interpolated filesystem root path.
    """
    config_path = tmp_path / 'config.yaml'
    config_data = {
        'registries': [
            {
                'name': 'example',
                'type': 'cache',
                'url': 'https://example.com',
                'ttl': '12h',
            }
        ],
        'registry': {
            'baseConfig': {
                'version': '0.1',
                'storage': {
                    'filesystem': {
                        'rootdirectory': str(tmp_path / '{name}'),
                    }
                },
                'proxy': {},
            }
        },
    }
    config_path.write_text(yaml.dump(config_data), encoding='utf-8')

    schedule = cleanup.build_schedule_from_config(str(config_path))
    assert schedule
    entry = schedule[0]
    assert entry['name'] == 'example'
    assert entry['storage_driver'] == 'filesystem'
    assert Path(entry['storage_path']).name == 'example'
