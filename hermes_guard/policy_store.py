"""Policy file loading helpers."""

from __future__ import annotations

from pathlib import Path

import yaml

from hermes_guard.models import Decision, PolicyConfig, PolicyRule

DEFAULT_POLICY_PATH = Path.home() / '.hermes' / 'guard-policy.yaml'
DEFAULT_GRANTS_PATH = Path.home() / '.hermes' / 'guard-grants.yaml'


def load_policy(path: Path | None = None) -> PolicyConfig:
    policy_path = Path(path or DEFAULT_POLICY_PATH)
    if not policy_path.exists():
        return PolicyConfig(defaults={}, channel_defaults={}, rules=())

    data = yaml.safe_load(policy_path.read_text(encoding='utf-8')) or {}
    defaults = dict(data.get('defaults') or {})
    channel_defaults = dict(data.get('channels') or {})
    rules = []
    for item in data.get('rules') or []:
        if not isinstance(item, dict):
            continue
        rules.append(
            PolicyRule.from_values(
                id=str(item['id']),
                actions=item.get('action') or (),
                channels=item.get('channel') or (),
                path=str(item.get('path') or ''),
                effect=Decision(str(item.get('effect') or 'confirm')),
                except_paths=item.get('except') or (),
                enabled=bool(item.get('enabled', True)),
            )
        )
    return PolicyConfig(defaults=defaults, channel_defaults=channel_defaults, rules=tuple(rules))
