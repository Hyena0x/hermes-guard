"""Minimal Hermes plugin entry for Hermes Guard.

This module exposes a `register(ctx)` function in the shape Hermes expects for
user/project plugins.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from hermes_guard.hermes_adapter import hermes_pre_tool_call


def register(ctx: Any) -> None:
    ctx.register_hook('pre_tool_call', _build_pre_tool_call_handler())


def _build_pre_tool_call_handler() -> Callable[..., dict[str, str] | None]:
    def _handler(**kwargs: Any) -> dict[str, str] | None:
        channel = str(kwargs.get('channel') or os.getenv('HERMES_GUARD_CHANNEL') or 'cli')
        policy_path = _optional_path(os.getenv('HERMES_GUARD_POLICY_PATH'))
        grants_path = _optional_path(os.getenv('HERMES_GUARD_GRANTS_PATH'))
        return hermes_pre_tool_call(
            tool_name=str(kwargs.get('tool_name') or ''),
            args=kwargs.get('args') if isinstance(kwargs.get('args'), dict) else {},
            task_id=str(kwargs.get('task_id') or ''),
            session_id=str(kwargs.get('session_id') or ''),
            tool_call_id=str(kwargs.get('tool_call_id') or ''),
            channel=channel,
            policy_path=policy_path,
            grants_path=grants_path,
        )

    return _handler


def _optional_path(value: str | None) -> Path | None:
    if not value:
        return None
    return Path(value).expanduser()
