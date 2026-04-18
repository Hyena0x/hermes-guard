"""Shared lightweight data models for Hermes Guard v0.1."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class Decision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    CONFIRM = "confirm"


@dataclass(frozen=True)
class PolicyRule:
    id: str
    actions: tuple[str, ...]
    channels: tuple[str, ...]
    path: str
    effect: Decision
    except_paths: tuple[str, ...] = ()
    enabled: bool = True

    @classmethod
    def from_values(
        cls,
        *,
        id: str,
        actions: Iterable[str],
        channels: Iterable[str],
        path: str,
        effect: Decision,
        except_paths: Iterable[str] = (),
        enabled: bool = True,
    ) -> "PolicyRule":
        return cls(
            id=id,
            actions=tuple(actions),
            channels=tuple(channels),
            path=path,
            effect=effect,
            except_paths=tuple(except_paths),
            enabled=enabled,
        )


@dataclass(frozen=True)
class PolicyConfig:
    defaults: dict[str, dict[str, str]]
    channel_defaults: dict[str, dict[str, str]]
    rules: tuple[PolicyRule, ...] = ()


@dataclass(frozen=True)
class GrantRecord:
    id: str
    actions: tuple[str, ...]
    channels: tuple[str, ...]
    path: str
    effect: Decision
    lifetime: str
    session_id: str | None = None
    created_at: str | None = None


@dataclass(frozen=True)
class PolicyDecision:
    decision: Decision
    rule_id: str | None = None
    reason: str | None = None
    next_step: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
