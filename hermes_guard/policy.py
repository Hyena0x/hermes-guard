"""Policy evaluation entry points."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from hermes_guard.grants import load_grants
from hermes_guard.models import Decision, GrantRecord, PolicyConfig, PolicyDecision, PolicyRule
from hermes_guard.path_rules import canonicalize_path
from hermes_guard.policy_store import load_policy
from hermes_guard.terminal_policy import terminal_verdict


TOOL_ACTIONS = {
    'read_file': 'read',
    'write_file': 'write',
    'patch': 'patch',
    'terminal': 'execute',
}

DEFAULT_DECISION = PolicyDecision(
    decision=Decision.CONFIRM,
    rule_id='guard-fallback-confirm',
    reason='No matching policy rule or channel default found.',
)


def evaluate_policy(
    *,
    tool_name: str,
    args: dict,
    channel: str,
    policy_path: Path | None = None,
    grants_path: Path | None = None,
    session_id: str | None = None,
    **kwargs,
) -> PolicyDecision:
    action = TOOL_ACTIONS.get(tool_name)
    if action is None:
        return DEFAULT_DECISION

    config = load_policy(policy_path)
    target_path = _extract_target_path(tool_name, args)
    if not target_path:
        return _default_decision(config, channel, action)

    canonical_path = canonicalize_path(target_path)
    if tool_name == 'terminal':
        terminal_decision = _evaluate_terminal_constraints(
            command=str(args.get('command') or ''),
            channel=channel,
            canonical_path=canonical_path,
            action=action,
        )
        if terminal_decision is not None:
            return terminal_decision
    matching_rules = _matching_rules(config.rules, action=action, channel=channel, canonical_path=canonical_path)
    matching_grants = _matching_grants(
        load_grants(grants_path),
        action=action,
        channel=channel,
        canonical_path=canonical_path,
        session_id=session_id,
    )

    if matching_rules['deny']:
        rule = matching_rules['deny'][0]
        return PolicyDecision(
            decision=Decision.DENY,
            rule_id=rule.id,
            reason=f'Action denied for {canonical_path}',
            metadata={'path': canonical_path, 'channel': channel, 'action': action},
        )
    if matching_rules['confirm']:
        rule = matching_rules['confirm'][0]
        return PolicyDecision(
            decision=Decision.CONFIRM,
            rule_id=rule.id,
            reason=f'Explicit confirmation required for {canonical_path}',
            next_step=_build_grant_command(channel=channel, action=action, canonical_path=canonical_path),
            metadata={'path': canonical_path, 'channel': channel, 'action': action},
        )
    if matching_grants:
        grant = matching_grants[0]
        return PolicyDecision(
            decision=Decision.ALLOW,
            rule_id=f'grant:{grant.id}',
            reason=f'Allowed by grant for {canonical_path}',
            metadata={'path': canonical_path, 'channel': channel, 'action': action},
        )
    if matching_rules['allow']:
        rule = matching_rules['allow'][0]
        return PolicyDecision(
            decision=Decision.ALLOW,
            rule_id=rule.id,
            reason=f'Allowed by matching policy rule for {canonical_path}',
            metadata={'path': canonical_path, 'channel': channel, 'action': action},
        )

    return _default_decision(config, channel, action, canonical_path=canonical_path)


def _extract_target_path(tool_name: str, args: dict) -> str | None:
    if tool_name in {'read_file', 'write_file', 'patch'}:
        return args.get('path')
    return args.get('workdir')


def _evaluate_terminal_constraints(
    *, command: str, channel: str, canonical_path: str, action: str
) -> PolicyDecision | None:
    verdict, reason = terminal_verdict(command, channel=channel)
    if verdict == 'allow':
        return None
    return PolicyDecision(
        decision=Decision.CONFIRM,
        rule_id=f'terminal-policy:{reason}',
        reason=f'Terminal command requires explicit confirmation for {canonical_path}',
        next_step=_build_grant_command(channel=channel, action=action, canonical_path=canonical_path),
        metadata={'path': canonical_path, 'channel': channel, 'action': action},
    )


def _matching_rules(
    rules: Iterable[PolicyRule], *, action: str, channel: str, canonical_path: str
) -> dict[str, list[PolicyRule]]:
    buckets: dict[str, list[PolicyRule]] = {'deny': [], 'confirm': [], 'allow': []}
    for rule in rules:
        if not rule.enabled:
            continue
        if action not in rule.actions:
            continue
        if channel not in rule.channels and '*' not in rule.channels:
            continue
        if not _path_matches(canonical_path, rule.path):
            continue
        deny_from_except = False
        for except_path in rule.except_paths:
            if _path_matches(canonical_path, except_path):
                buckets['deny'].append(
                    PolicyRule(
                        id=f'{rule.id}#except',
                        actions=rule.actions,
                        channels=rule.channels,
                        path=except_path,
                        effect=Decision.DENY,
                    )
                )
                deny_from_except = True
                break
        if deny_from_except:
            continue
        buckets[rule.effect.value].append(rule)

    for key in buckets:
        buckets[key].sort(key=lambda rule: _specificity(rule.path), reverse=True)
    return buckets


def _path_matches(canonical_path: str, pattern: str) -> bool:
    if pattern.endswith('/**'):
        canonical_pattern = str(Path(canonicalize_path(pattern.rstrip('/**'))))
        return canonical_path == canonical_pattern or canonical_path.startswith(canonical_pattern + '/')
    return Path(canonical_path).match(canonicalize_path(pattern))


def _specificity(pattern: str) -> int:
    return len(pattern.replace('*', ''))


def _matching_grants(
    grants: Iterable[GrantRecord],
    *,
    action: str,
    channel: str,
    canonical_path: str,
    session_id: str | None,
) -> list[GrantRecord]:
    matches: list[GrantRecord] = []
    for grant in grants:
        if action not in grant.actions:
            continue
        if channel not in grant.channels and '*' not in grant.channels:
            continue
        if grant.lifetime == 'session' and grant.session_id != session_id:
            continue
        if not _path_matches(canonical_path, grant.path):
            continue
        matches.append(grant)
    matches.sort(key=lambda grant: _specificity(grant.path), reverse=True)
    return matches


def _build_grant_command(*, channel: str, action: str, canonical_path: str) -> str:
    path_segment = f' --path "{canonical_path}"' if canonical_path else ''
    return f'guard grant --channel {channel} --action {action}{path_segment} --lifetime session'


def _default_decision(
    config: PolicyConfig, channel: str, action: str, canonical_path: str = ''
) -> PolicyDecision:
    channel_defaults = config.channel_defaults.get(channel, {})
    if action in channel_defaults:
        decision = Decision(channel_defaults[action])
        return PolicyDecision(
            decision=decision,
            rule_id=f'channel-default:{channel}:{action}',
            reason=f'Channel default applied for {channel}:{action}',
            next_step=(
                _build_grant_command(channel=channel, action=action, canonical_path=canonical_path)
                if decision == Decision.CONFIRM
                else None
            ),
            metadata={'path': canonical_path, 'channel': channel, 'action': action},
        )

    global_defaults = config.defaults.get('global', {})
    if action in global_defaults:
        decision = Decision(global_defaults[action])
        return PolicyDecision(
            decision=decision,
            rule_id=f'global-default:{action}',
            reason=f'Global default applied for {action}',
            next_step=(
                _build_grant_command(channel=channel, action=action, canonical_path=canonical_path)
                if decision == Decision.CONFIRM
                else None
            ),
            metadata={'path': canonical_path, 'channel': channel, 'action': action},
        )

    return DEFAULT_DECISION
