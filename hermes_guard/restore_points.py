"""Restore point helpers for Hermes Guard updates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

RESTORE_POINTS_DIR = Path.home() / '.hermes' / 'guard' / 'restore-points'


def ensure_restore_points_dir(path: Path | None = None) -> Path:
    """Create and return the restore points directory."""
    directory = Path(path or RESTORE_POINTS_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def write_restore_point(data: dict[str, Any], directory: Path | None = None) -> Path:
    """Serialize a restore point dict to a timestamped JSON file."""
    restore_dir = ensure_restore_points_dir(directory)
    created_at = str(data.get('created_at', 'restore-point')).replace(':', '-').replace('/', '-')
    file_path = restore_dir / f'{created_at}.json'
    file_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding='utf-8')
    return file_path


def load_latest_restore_point(directory: Path | None = None) -> dict[str, Any] | None:
    """Return the most recent restore point dict, or None if none exist."""
    restore_dir = Path(directory or RESTORE_POINTS_DIR)
    if not restore_dir.exists():
        return None
    json_files = sorted(restore_dir.glob('*.json'), reverse=True)
    if not json_files:
        return None
    return json.loads(json_files[0].read_text(encoding='utf-8'))
