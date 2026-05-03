from hermes_guard.models import Decision
from hermes_guard.policy import evaluate_policy
from hermes_guard.policy_store import load_policy


def test_load_policy_parses_defaults_and_rules(tmp_path):
    policy_path = tmp_path / 'guard-policy.yaml'
    policy_path.write_text(
        '''version: 1

defaults:
  global:
    read: deny
    write: deny
    patch: deny
    execute: confirm

channels:
  cli:
    read: allow
    write: confirm

rules:
  - id: allow-project
    action: [read, write]
    channel: [cli]
    path: "/workspace/project/**"
    effect: allow
    except:
      - "/workspace/project/.env"
''',
        encoding='utf-8',
    )

    config = load_policy(policy_path)

    assert config.defaults['global']['read'] == 'deny'
    assert config.channel_defaults['cli']['write'] == 'confirm'
    assert len(config.rules) == 1
    assert config.rules[0].id == 'allow-project'
    assert config.rules[0].except_paths == ('/workspace/project/.env',)


def test_evaluate_policy_allows_matching_rule(tmp_path):
    policy_path = tmp_path / 'guard-policy.yaml'
    policy_path.write_text(
        '''version: 1

defaults:
  global:
    read: deny

channels:
  cli:
    read: deny

rules:
  - id: allow-project-read
    action: [read]
    channel: [cli]
    path: "''' + str(tmp_path / 'project') + '''/**"
    effect: allow
''',
        encoding='utf-8',
    )
    target = tmp_path / 'project' / 'notes.txt'
    target.parent.mkdir(parents=True)
    target.write_text('hello', encoding='utf-8')

    decision = evaluate_policy(
        tool_name='read_file',
        args={'path': str(target)},
        channel='cli',
        policy_path=policy_path,
    )

    assert decision.decision == Decision.ALLOW
    assert decision.rule_id == 'allow-project-read'


def test_evaluate_policy_except_path_becomes_deny(tmp_path):
    project_dir = tmp_path / 'project'
    secret_file = project_dir / '.env'
    secret_file.parent.mkdir(parents=True)
    secret_file.write_text('SECRET=1', encoding='utf-8')

    policy_path = tmp_path / 'guard-policy.yaml'
    policy_path.write_text(
        '''version: 1

defaults:
  global:
    read: deny

channels:
  cli:
    read: deny

rules:
  - id: allow-project-read
    action: [read]
    channel: [cli]
    path: "''' + str(project_dir) + '''/**"
    effect: allow
    except:
      - "''' + str(secret_file) + '''"
''',
        encoding='utf-8',
    )

    decision = evaluate_policy(
        tool_name='read_file',
        args={'path': str(secret_file)},
        channel='cli',
        policy_path=policy_path,
    )

    assert decision.decision == Decision.DENY
    assert decision.rule_id == 'allow-project-read#except'


def test_evaluate_policy_falls_back_to_channel_default(tmp_path):
    policy_path = tmp_path / 'guard-policy.yaml'
    policy_path.write_text(
        '''version: 1

defaults:
  global:
    read: deny

channels:
  telegram:
    read: confirm
''',
        encoding='utf-8',
    )
    target = tmp_path / 'notes.txt'
    target.write_text('hello', encoding='utf-8')

    decision = evaluate_policy(
        tool_name='read_file',
        args={'path': str(target)},
        channel='telegram',
        policy_path=policy_path,
    )

    assert decision.decision == Decision.CONFIRM
    assert decision.rule_id == 'channel-default:telegram:read'
    assert 'guard grant' in (decision.next_step or '')
    assert '--channel telegram' in (decision.next_step or '')
    assert '--action read' in (decision.next_step or '')
    assert '--lifetime persistent' in (decision.next_step or '')


def test_confirm_rule_includes_actionable_next_step(tmp_path):
    policy_path = tmp_path / 'guard-policy.yaml'
    target = tmp_path / 'project' / 'config.yaml'
    target.parent.mkdir(parents=True)
    target.write_text('name: demo\n', encoding='utf-8')
    policy_path.write_text(
        '''version: 1

defaults:
  global:
    write: deny

channels:
  cli:
    write: deny

rules:
  - id: confirm-project-write
    action: [write]
    channel: [cli]
    path: "''' + str(tmp_path / 'project') + '''/**"
    effect: confirm
''',
        encoding='utf-8',
    )

    decision = evaluate_policy(
        tool_name='write_file',
        args={'path': str(target)},
        channel='cli',
        policy_path=policy_path,
    )

    assert decision.decision == Decision.CONFIRM
    assert decision.rule_id == 'confirm-project-write'
    assert decision.next_step is not None
    assert 'guard grant' in decision.next_step
    assert '--channel cli' in decision.next_step
    assert '--action write' in decision.next_step
    assert str(target) in decision.next_step
    assert '--lifetime persistent' in decision.next_step


def test_persistent_grant_allows_path_when_policy_default_denies(tmp_path):
    policy_path = tmp_path / 'guard-policy.yaml'
    policy_path.write_text(
        '''version: 1

defaults:
  global:
    read: deny
''',
        encoding='utf-8',
    )
    grants_path = tmp_path / 'guard-grants.yaml'
    target = tmp_path / 'project' / 'notes.txt'
    target.parent.mkdir(parents=True)
    target.write_text('hello', encoding='utf-8')

    from hermes_guard.grants import add_grant
    add_grant(
        grants_path,
        action='read',
        channel='cli',
        target_path=str(tmp_path / 'project' / '**'),
        lifetime='persistent',
    )

    decision = evaluate_policy(
        tool_name='read_file',
        args={'path': str(target)},
        channel='cli',
        policy_path=policy_path,
        grants_path=grants_path,
    )

    assert decision.decision == Decision.ALLOW
    assert decision.rule_id.startswith('grant:')


def test_session_grant_is_ignored_without_matching_session_id(tmp_path):
    policy_path = tmp_path / 'guard-policy.yaml'
    policy_path.write_text(
        '''version: 1

defaults:
  global:
    read: deny
''',
        encoding='utf-8',
    )
    grants_path = tmp_path / 'guard-grants.yaml'
    target = tmp_path / 'project' / 'notes.txt'
    target.parent.mkdir(parents=True)
    target.write_text('hello', encoding='utf-8')

    from hermes_guard.grants import add_grant
    add_grant(
        grants_path,
        action='read',
        channel='cli',
        target_path=str(tmp_path / 'project' / '**'),
        lifetime='session',
        session_id='session-123',
    )

    decision = evaluate_policy(
        tool_name='read_file',
        args={'path': str(target)},
        channel='cli',
        policy_path=policy_path,
        grants_path=grants_path,
        session_id='other-session',
    )

    assert decision.decision == Decision.DENY
    assert decision.rule_id == 'global-default:read'


def test_session_grant_without_session_id_is_ignored(tmp_path):
    policy_path = tmp_path / 'guard-policy.yaml'
    policy_path.write_text(
        '''version: 1

defaults:
  global:
    read: deny
''',
        encoding='utf-8',
    )
    grants_path = tmp_path / 'guard-grants.yaml'
    target = tmp_path / 'project' / 'notes.txt'
    target.parent.mkdir(parents=True)
    target.write_text('hello', encoding='utf-8')
    grants_path.write_text(
        '''version: 1
grants:
  - id: malformed-session-grant
    action: [read]
    channel: [cli]
    path: "''' + str(tmp_path / 'project' / '**') + '''"
    effect: allow
    lifetime: session
''',
        encoding='utf-8',
    )

    decision = evaluate_policy(
        tool_name='read_file',
        args={'path': str(target)},
        channel='cli',
        policy_path=policy_path,
        grants_path=grants_path,
    )

    assert decision.decision == Decision.DENY
    assert decision.rule_id == 'global-default:read'
