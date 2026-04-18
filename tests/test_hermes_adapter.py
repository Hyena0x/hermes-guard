from hermes_guard.hermes_adapter import hermes_pre_tool_call


def test_adapter_returns_none_for_allowed_action(tmp_path):
    policy_path = tmp_path / 'guard-policy.yaml'
    target = tmp_path / 'project' / 'notes.txt'
    target.parent.mkdir(parents=True)
    target.write_text('hello', encoding='utf-8')
    policy_path.write_text(
        '''version: 1

defaults:
  global:
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

    result = hermes_pre_tool_call(
        tool_name='read_file',
        args={'path': str(target)},
        session_id='s1',
        channel='cli',
        policy_path=policy_path,
    )

    assert result is None


def test_adapter_blocks_confirm_with_actionable_message(tmp_path):
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
    write: confirm
''',
        encoding='utf-8',
    )

    result = hermes_pre_tool_call(
        tool_name='write_file',
        args={'path': str(target)},
        session_id='s2',
        channel='cli',
        policy_path=policy_path,
    )

    assert result is not None
    assert result['action'] == 'block'
    assert 'guard grant' in result['message']
    assert str(target) in result['message']


def test_adapter_blocks_denied_action(tmp_path):
    policy_path = tmp_path / 'guard-policy.yaml'
    target = tmp_path / '.env'
    target.write_text('SECRET=1', encoding='utf-8')
    policy_path.write_text(
        '''version: 1

defaults:
  global:
    read: deny

rules:
  - id: deny-env
    action: [read]
    channel: [cli]
    path: "''' + str(target) + '''"
    effect: deny
''',
        encoding='utf-8',
    )

    result = hermes_pre_tool_call(
        tool_name='read_file',
        args={'path': str(target)},
        session_id='s3',
        channel='cli',
        policy_path=policy_path,
    )

    assert result is not None
    assert result['action'] == 'block'
    assert 'deny-env' in result['message']
    assert 'Action: read' in result['message']


def test_adapter_fails_closed_on_internal_error(monkeypatch):
    import hermes_guard.hermes_adapter as adapter

    def boom(**kwargs):
        raise RuntimeError('boom')

    monkeypatch.setattr(adapter, 'evaluate_policy', boom)

    result = adapter.hermes_pre_tool_call(
        tool_name='read_file',
        args={'path': '/tmp/demo.txt'},
        session_id='s4',
        channel='cli',
    )

    assert result is not None
    assert result['action'] == 'block'
    assert 'Hermes Guard internal error' in result['message']
