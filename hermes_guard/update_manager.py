"""Tag-first update manager for Hermes Guard."""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from hermes_guard import __version__
from hermes_guard.restore_points import load_latest_restore_point, write_restore_point

DEFAULT_HERMES_REPO = Path.home() / '.hermes' / 'hermes-agent'


def is_git_repo(path: Path) -> bool:
    return (path / '.git').exists()


def list_tags(path: Path, *, limit: int = 20) -> list[str]:
    if not is_git_repo(path):
        return []
    result = _run_git(path, ['tag', '--sort=-version:refname'])
    if result.returncode != 0:
        return []
    tags = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return tags[:limit]


def get_update_status(path: Path) -> dict[str, object]:
    repo = Path(path)
    if not is_git_repo(repo):
        return {
            'repo_path': str(repo),
            'is_git_repo': False,
            'error': 'not-a-git-repo',
        }

    commit = _git_stdout(repo, ['rev-parse', 'HEAD'])
    tag = _git_stdout(repo, ['describe', '--tags', '--exact-match'], allow_failure=True) or None
    branch = _git_stdout(repo, ['rev-parse', '--abbrev-ref', 'HEAD'])
    dirty = bool(_git_stdout(repo, ['status', '--short']))
    return {
        'repo_path': str(repo),
        'is_git_repo': True,
        'dirty': dirty,
        'commit': commit,
        'tag': tag,
        'branch': branch,
        'version': __version__,
    }


def create_restore_point(path: Path, *, restore_dir: Path | None = None) -> dict[str, object]:
    repo = Path(path)
    status = get_update_status(repo)
    if not status.get('is_git_repo'):
        raise ValueError('not-a-git-repo')

    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%SZ')
    default_dir = Path.home() / '.hermes' / 'guard' / 'restore-points'
    pip_freeze_path = Path(restore_dir or default_dir) / f'{timestamp}-pip-freeze.txt'
    pip_freeze_path.parent.mkdir(parents=True, exist_ok=True)
    freeze_output = _python_stdout(['-m', 'pip', 'freeze'], allow_failure=True)
    pip_freeze_path.write_text(freeze_output, encoding='utf-8')

    restore_point = {
        'created_at': timestamp,
        'repo_path': str(repo),
        'git_branch': status['branch'],
        'git_commit': status['commit'],
        'git_tag': status['tag'],
        'version': status['version'],
        'dirty': status['dirty'],
        'python_executable': _python_stdout(['-c', 'import sys; print(sys.executable)']).strip(),
        'python_version': _python_stdout(['--version']).strip(),
        'pip_freeze_path': str(pip_freeze_path),
    }
    write_restore_point(restore_point, restore_dir)
    return restore_point


def apply_tag(
    path: Path, tag: str, *, restore_dir: Path | None = None, allow_dirty: bool = False
) -> dict[str, object]:
    repo = Path(path)
    status = get_update_status(repo)
    if not status.get('is_git_repo'):
        raise ValueError('not-a-git-repo')
    if status.get('dirty') and not allow_dirty:
        raise ValueError('dirty-working-tree')

    restore_point = create_restore_point(repo, restore_dir=restore_dir)
    fetch_result = _run_git(repo, ['fetch', '--tags'])
    if fetch_result.returncode != 0:
        raise RuntimeError(fetch_result.stderr.strip() or 'git fetch --tags failed')
    checkout_result = _run_git(repo, ['checkout', tag])
    if checkout_result.returncode != 0:
        raise RuntimeError(checkout_result.stderr.strip() or f'git checkout {tag} failed')

    return {
        'repo_path': str(repo),
        'applied_tag': tag,
        'restore_point': restore_point,
    }


def rollback_to_latest_restore_point(
    path: Path, *, restore_dir: Path | None = None
) -> dict[str, object]:
    repo = Path(path)
    status = get_update_status(repo)
    if not status.get('is_git_repo'):
        raise ValueError('not-a-git-repo')

    restore_point = load_latest_restore_point(restore_dir)
    if not restore_point:
        raise ValueError('no-restore-point')

    target_ref = restore_point.get('git_tag') or restore_point.get('git_commit')
    if not target_ref:
        raise ValueError('invalid-restore-point')

    checkout_result = _run_git(repo, ['checkout', str(target_ref)])
    if checkout_result.returncode != 0:
        raise RuntimeError(checkout_result.stderr.strip() or f'git checkout {target_ref} failed')

    return {
        'repo_path': str(repo),
        'restored_ref': str(target_ref),
        'restore_point': restore_point,
    }


def _run_git(path: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(['git', *args], cwd=path, text=True, capture_output=True)


def _git_stdout(path: Path, args: list[str], *, allow_failure: bool = False) -> str:
    result = _run_git(path, args)
    if result.returncode != 0:
        if allow_failure:
            return ''
        raise RuntimeError(result.stderr.strip() or f'git command failed: {args}')
    return result.stdout.strip()


def _python_stdout(args: list[str], *, allow_failure: bool = False) -> str:
    result = subprocess.run(['python3', *args], text=True, capture_output=True)
    if result.returncode != 0:
        if allow_failure:
            return ''
        raise RuntimeError(result.stderr.strip() or f'python command failed: {args}')
    return (result.stdout or result.stderr).strip()
