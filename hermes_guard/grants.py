"""Dynamic grant storage helpers."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import yaml

try:
    from filelock import FileLock
except ImportError:  # pragma: no cover
    class FileLock:  # type: ignore[override]
        def __init__(self, *args, **kwargs):
            self.args = args

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

from hermes_guard.models import Decision, GrantRecord
from hermes_guard.policy_store import DEFAULT_GRANTS_PATH


def grants_lock_path(path: Path | None = None) -> Path:
    grants_path = path or DEFAULT_GRANTS_PATH
    return grants_path.with_suffix(grants_path.suffix + '.lock')


def acquire_grants_lock(path: Path | None = None) -> FileLock:
    return FileLock(str(grants_lock_path(path)))


@contextmanager
def locked_grants_file(path: Path | None = None):
    lock = acquire_grants_lock(path)
    with lock:
        yield


def load_grants(path: Path | None = None) -> list[GrantRecord]:
    grants_path = Path(path or DEFAULT_GRANTS_PATH)
    if not grants_path.exists():
        return []

    data = yaml.safe_load(grants_path.read_text(encoding='utf-8')) or {}
    items = []
    for grant in data.get('grants') or []:
        if not isinstance(grant, dict):
            continue
        items.append(
            GrantRecord(
                id=str(grant['id']),
                actions=tuple(grant.get('action') or []),
                channels=tuple(grant.get('channel') or []),
                path=str(grant.get('path') or ''),
                effect=Decision(str(grant.get('effect') or 'allow')),
                lifetime=str(grant.get('lifetime') or 'persistent'),
                session_id=grant.get('session_id'),
                created_at=grant.get('created_at'),
            )
        )
    return items


def add_grant(
    grants_path: Path | None = None,
    *,
    action: str,
    channel: str,
    target_path: str,
    lifetime: str,
    session_id: str | None = None,
) -> GrantRecord:
    if lifetime == 'session' and not session_id:
        raise ValueError('Session grants require --session-id. Use --lifetime persistent when no stable session id is available.')

    grant = GrantRecord(
        id=f'grant-{uuid4().hex[:12]}',
        actions=(action,),
        channels=(channel,),
        path=target_path,
        effect=Decision.ALLOW,
        lifetime=lifetime,
        session_id=session_id,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    path_obj = Path(grants_path or DEFAULT_GRANTS_PATH)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    with locked_grants_file(path_obj):
        current = load_grants(path_obj)
        current.append(grant)
        _write_grants(path_obj, current)
    return grant


def revoke_grant(grants_path: Path | None = None, grant_id: str = '') -> bool:
    path_obj = Path(grants_path or DEFAULT_GRANTS_PATH)
    with locked_grants_file(path_obj):
        current = load_grants(path_obj)
        kept = [grant for grant in current if grant.id != grant_id]
        if len(kept) == len(current):
            return False
        _write_grants(path_obj, kept)
        return True


def _write_grants(path: Path, grants: list[GrantRecord]) -> None:
    payload = {
        'version': 1,
        'grants': [
            {
                'id': grant.id,
                'action': list(grant.actions),
                'channel': list(grant.channels),
                'path': grant.path,
                'effect': grant.effect.value,
                'lifetime': grant.lifetime,
                'session_id': grant.session_id,
                'created_at': grant.created_at,
            }
            for grant in grants
        ],
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding='utf-8')
