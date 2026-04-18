"""Minimal Hermes plugin adapter for Hermes Guard v0.1.

This bridges Hermes pre_tool_call hook inputs into the local policy engine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hermes_guard.policy import evaluate_policy


def hermes_pre_tool_call(
    *,
    tool_name: str,
    args: dict[str, Any] | None,
    task_id: str = '',
    session_id: str = '',
    tool_call_id: str = '',
    channel: str = 'cli',
    policy_path: Path | None = None,
    grants_path: Path | None = None,
) -> dict[str, str] | None:
    try:
        decision = evaluate_policy(
            tool_name=tool_name,
            args=args if isinstance(args, dict) else {},
            channel=channel,
            policy_path=policy_path,
            grants_path=grants_path,
            session_id=session_id or None,
            task_id=task_id,
            tool_call_id=tool_call_id,
        )
    except Exception as exc:
        return {
            'action': 'block',
            'message': f'Hermes Guard internal error while checking {tool_name}: {exc}',
        }

    if decision.decision == 'allow':
        return None

    message = _format_block_message(
        tool_name=tool_name,
        decision=decision.decision.value if hasattr(decision.decision, 'value') else str(decision.decision),
        rule_id=decision.rule_id or 'unknown-rule',
        reason=decision.reason or 'Blocked by Hermes Guard.',
        next_step=decision.next_step,
        metadata=decision.metadata,
    )
    return {
        'action': 'block',
        'message': message,
    }


def _format_block_message(*, tool_name: str, decision: str, rule_id: str, reason: str, next_step: str | None, metadata: dict[str, str]) -> str:
    lines = [
        'Blocked by Hermes Guard.',
        f'Tool: {tool_name}',
        f'Action: {metadata.get("action", decision)}',
        f'Channel: {metadata.get("channel", "unknown")}',
    ]
    if metadata.get('path'):
        lines.append(f'Path: {metadata["path"]}')
    lines.extend([
        f'Matched rule: {rule_id}',
        f'Reason: {reason}',
    ])
    if next_step:
        lines.append(f'Next step: {next_step}')
    return '\n'.join(lines)
