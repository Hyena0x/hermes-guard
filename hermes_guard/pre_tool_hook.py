"""Hermes pre-tool hook integration points.

The real Hermes plugin wiring will be added later.
This module currently establishes the required fail-closed outer boundary.
"""

from __future__ import annotations

from hermes_guard.models import Decision, PolicyDecision
from hermes_guard.policy import evaluate_policy

ERROR_DECISION = PolicyDecision(
    decision=Decision.CONFIRM,
    rule_id='guard-internal-error',
    reason='Hermes Guard failed while evaluating the request.',
)


def pre_tool_check(*args, **kwargs) -> PolicyDecision:
    try:
        return evaluate_policy(*args, **kwargs)
    except Exception:
        return ERROR_DECISION
