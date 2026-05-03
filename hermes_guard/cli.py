"""Minimal CLI surface for Hermes Guard."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence, TextIO

from hermes_guard.grants import add_grant, load_grants, revoke_grant
from hermes_guard.update_manager import (
    apply_tag,
    create_restore_point,
    get_update_status,
    list_tags,
    rollback_to_latest_restore_point,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='guard', description='Hermes Guard CLI')
    subparsers = parser.add_subparsers(dest='command')

    grant_parser = subparsers.add_parser('grant', help='Create a grant')
    grant_parser.add_argument('--channel', required=True)
    grant_parser.add_argument('--action', required=True)
    grant_parser.add_argument('--path', required=True)
    grant_parser.add_argument('--lifetime', choices=['session', 'persistent'], default='session')
    grant_parser.add_argument('--session-id')
    grant_parser.add_argument('--grants-path')

    revoke_parser = subparsers.add_parser('revoke', help='Revoke a grant')
    revoke_parser.add_argument('--id', required=True)
    revoke_parser.add_argument('--grants-path')

    grants_parser = subparsers.add_parser('grants', help='List active grants')
    grants_parser.add_argument('--grants-path')

    update_parser = subparsers.add_parser('update', help='Update operations')
    update_subparsers = update_parser.add_subparsers(dest='update_command')
    status_parser = update_subparsers.add_parser('status', help='Show current update status')
    status_parser.add_argument('--repo-path')
    list_parser = update_subparsers.add_parser('list', help='List available tags')
    list_parser.add_argument('--repo-path')
    checkpoint_parser = update_subparsers.add_parser('checkpoint', help='Create a restore point')
    checkpoint_parser.add_argument('--repo-path')
    checkpoint_parser.add_argument('--restore-dir')
    apply_parser = update_subparsers.add_parser('apply', help='Apply a tag')
    apply_parser.add_argument('--tag', required=True)
    apply_parser.add_argument('--repo-path')
    apply_parser.add_argument('--restore-dir')
    apply_parser.add_argument('--allow-dirty', action='store_true')
    rollback_parser = update_subparsers.add_parser('rollback', help='Rollback to latest restore point')
    rollback_parser.add_argument('--repo-path')
    rollback_parser.add_argument('--restore-dir')

    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    parser = build_parser()
    stream = stdout or sys.stdout
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == 'grant':
        try:
            grant = add_grant(
                Path(args.grants_path) if args.grants_path else None,
                action=args.action,
                channel=args.channel,
                target_path=args.path,
                lifetime=args.lifetime,
                session_id=args.session_id,
            )
        except ValueError as exc:
            print(str(exc), file=stream)
            return 1
        print(
            f'Grant created: {grant.id}  {grant.actions[0]}  {grant.channels[0]}  {grant.path}  ({grant.lifetime})',
            file=stream,
        )
        return 0

    if args.command == 'revoke':
        removed = revoke_grant(Path(args.grants_path) if args.grants_path else None, args.id)
        if removed:
            print(f'Revoked grant {args.id}', file=stream)
            return 0
        print(f'Grant not found: {args.id}', file=stream)
        return 1

    if args.command == 'grants':
        grants = load_grants(Path(args.grants_path) if args.grants_path else None)
        if not grants:
            print('No active grants.', file=stream)
            return 0
        print(f'{"ID":<26}  {"ACTION":<8}  {"CHANNEL":<10}  {"PATH":<40}  LIFETIME', file=stream)
        print('-' * 100, file=stream)
        for grant in grants:
            print(
                f'{grant.id:<26}  {grant.actions[0]:<8}  {grant.channels[0]:<10}  {grant.path:<40}  {grant.lifetime}',
                file=stream,
            )
        return 0

    if args.command == 'update':
        repo_path = Path(args.repo_path).expanduser() if getattr(args, 'repo_path', None) else None
        resolved_repo = repo_path or Path.home() / '.hermes' / 'hermes-agent'
        if args.update_command == 'status':
            status = get_update_status(resolved_repo)
            print('Update status:', file=stream)
            for key, value in status.items():
                print(f'  {key}: {value}', file=stream)
            return 0
        if args.update_command == 'list':
            tags = list_tags(resolved_repo)
            if not tags:
                print('No tags found.', file=stream)
                return 0
            print('Available tags:', file=stream)
            for tag in tags:
                print(f'  {tag}', file=stream)
            return 0
        if args.update_command == 'checkpoint':
            restore_point = create_restore_point(
                resolved_repo,
                restore_dir=Path(args.restore_dir).expanduser() if getattr(args, 'restore_dir', None) else None,
            )
            print(f'Restore point created at {restore_point["created_at"]}  commit {restore_point["git_commit"]}', file=stream)
            return 0
        if args.update_command == 'apply':
            try:
                result = apply_tag(
                    resolved_repo,
                    args.tag,
                    restore_dir=Path(args.restore_dir).expanduser() if getattr(args, 'restore_dir', None) else None,
                    allow_dirty=bool(getattr(args, 'allow_dirty', False)),
                )
            except ValueError as exc:
                print(f'Update apply failed: {exc}', file=stream)
                return 1
            print(
                f'Applied tag {result["applied_tag"]}  (restore point: {result["restore_point"]["created_at"]})',
                file=stream,
            )
            return 0
        if args.update_command == 'rollback':
            try:
                result = rollback_to_latest_restore_point(
                    resolved_repo,
                    restore_dir=Path(args.restore_dir).expanduser() if getattr(args, 'restore_dir', None) else None,
                )
            except ValueError as exc:
                print(f'Rollback failed: {exc}', file=stream)
                return 1
            print(f'Rolled back to {result["restored_ref"]}', file=stream)
            return 0

    parser.print_help(file=stream)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
