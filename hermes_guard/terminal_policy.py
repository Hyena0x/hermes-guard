"""Conservative terminal handling for Hermes Guard v0.1."""

from __future__ import annotations

SAFE_CLI_PREFIXES = (
    'pwd',
    'which',
    'date',
    'uname',
    'git status',
    'git diff',
    'python --version',
)

DANGEROUS_TOKENS = (
    'rm ',
    'mv ',
    'chmod ',
    'chown ',
    'git reset --hard',
    'git clean -fd',
    'pip install',
    'pip uninstall',
    'uv pip install',
    'brew install',
    'brew uninstall',
)

COMPLEX_SHELL_TOKENS = (
    '&&',
    '||',
    ';',
    '|',
    '>',
    '>>',
    '$(',
    '`',
)


def terminal_verdict(command: str, *, channel: str) -> tuple[str, str]:
    """Return a (verdict, reason) tuple for the given terminal command.

    verdict is one of: 'allow', 'confirm'.
    reason is a short machine-readable label explaining the decision.
    """
    normalized = (command or '').strip()
    if not normalized:
        return 'confirm', 'empty-command'

    if channel != 'cli':
        return 'confirm', 'non-cli'

    lowered = normalized.lower()
    if any(token in lowered for token in COMPLEX_SHELL_TOKENS):
        return 'confirm', 'complex-command'

    if any(token in lowered for token in DANGEROUS_TOKENS):
        return 'confirm', 'dangerous-command'

    if normalized in SAFE_CLI_PREFIXES:
        return 'allow', 'safe-cli'

    if any(normalized.startswith(prefix + ' ') for prefix in ('python', 'git', 'ls', 'cat', 'echo')):
        return 'confirm', 'unknown-args'

    return 'confirm', 'unknown-command'
