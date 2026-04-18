from hermes_guard.models import Decision
from hermes_guard.policy import evaluate_policy
from hermes_guard.terminal_policy import terminal_verdict


def test_terminal_verdict_allows_safe_cli_readonly_command():
    verdict, reason = terminal_verdict('git status', channel='cli')

    assert verdict == 'allow'
    assert reason == 'safe-cli'


def test_terminal_verdict_confirms_dangerous_command():
    verdict, reason = terminal_verdict('rm -rf /tmp/demo', channel='cli')

    assert verdict == 'confirm'
    assert reason == 'dangerous-command'


def test_terminal_verdict_confirms_chained_command():
    verdict, reason = terminal_verdict('pwd && ls', channel='cli')

    assert verdict == 'confirm'
    assert reason == 'complex-command'


def test_terminal_policy_allows_safe_cli_command_in_allowed_workspace(tmp_path):
    policy_path = tmp_path / 'guard-policy.yaml'
    workdir = tmp_path / 'project'
    workdir.mkdir()
    policy_path.write_text(
        '''version: 1

defaults:
  global:
    execute: confirm

rules:
  - id: allow-project-exec
    action: [execute]
    channel: [cli]
    path: "''' + str(workdir) + '''/**"
    effect: allow
''',
        encoding='utf-8',
    )

    decision = evaluate_policy(
        tool_name='terminal',
        args={'command': 'git status', 'workdir': str(workdir)},
        channel='cli',
        policy_path=policy_path,
    )

    assert decision.decision == Decision.ALLOW
    assert decision.rule_id == 'allow-project-exec'


def test_terminal_policy_confirms_dangerous_command_even_in_allowed_workspace(tmp_path):
    policy_path = tmp_path / 'guard-policy.yaml'
    workdir = tmp_path / 'project'
    workdir.mkdir()
    policy_path.write_text(
        '''version: 1

defaults:
  global:
    execute: confirm

rules:
  - id: allow-project-exec
    action: [execute]
    channel: [cli]
    path: "''' + str(workdir) + '''/**"
    effect: allow
''',
        encoding='utf-8',
    )

    decision = evaluate_policy(
        tool_name='terminal',
        args={'command': 'rm -rf build', 'workdir': str(workdir)},
        channel='cli',
        policy_path=policy_path,
    )

    assert decision.decision == Decision.CONFIRM
    assert decision.rule_id == 'terminal-policy:dangerous-command'
    assert decision.next_step is not None


def test_terminal_policy_confirms_safe_command_on_non_cli_channel(tmp_path):
    policy_path = tmp_path / 'guard-policy.yaml'
    workdir = tmp_path / 'project'
    workdir.mkdir()
    policy_path.write_text(
        '''version: 1

defaults:
  global:
    execute: confirm

rules:
  - id: allow-project-exec
    action: [execute]
    channel: [telegram]
    path: "''' + str(workdir) + '''/**"
    effect: allow
''',
        encoding='utf-8',
    )

    decision = evaluate_policy(
        tool_name='terminal',
        args={'command': 'git status', 'workdir': str(workdir)},
        channel='telegram',
        policy_path=policy_path,
    )

    assert decision.decision == Decision.CONFIRM
    assert decision.rule_id == 'terminal-policy:non-cli'
