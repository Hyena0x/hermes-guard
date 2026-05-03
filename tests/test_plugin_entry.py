from hermes_guard.plugin_entry import register


class DummyContext:
    def __init__(self):
        self.calls = []

    def register_hook(self, hook_name, callback):
        self.calls.append((hook_name, callback))


def test_register_adds_pre_tool_call_hook():
    ctx = DummyContext()

    register(ctx)

    assert len(ctx.calls) == 1
    assert ctx.calls[0][0] == 'pre_tool_call'
    assert callable(ctx.calls[0][1])


def test_registered_hook_delegates_to_adapter(tmp_path, monkeypatch):
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
    monkeypatch.setenv('HERMES_GUARD_POLICY_PATH', str(policy_path))
    monkeypatch.setenv('HERMES_GUARD_CHANNEL', 'cli')

    ctx = DummyContext()
    register(ctx)
    hook = ctx.calls[0][1]

    result = hook(
        tool_name='write_file',
        args={'path': str(target)},
        session_id='plugin-session',
        task_id='task-1',
        tool_call_id='call-1',
    )

    assert result is not None
    assert result['action'] == 'block'
    assert 'guard grant' in result['message']
    assert str(target) in result['message']


def test_registered_hook_uses_explicit_channel_override(monkeypatch, tmp_path):
    policy_path = tmp_path / 'guard-policy.yaml'
    target = tmp_path / 'notes.txt'
    target.write_text('hello', encoding='utf-8')
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
    monkeypatch.setenv('HERMES_GUARD_POLICY_PATH', str(policy_path))

    ctx = DummyContext()
    register(ctx)
    hook = ctx.calls[0][1]

    result = hook(
        tool_name='read_file',
        args={'path': str(target)},
        session_id='plugin-session',
        channel='telegram',
    )

    assert result is not None
    assert result['action'] == 'block'
    assert 'Channel: telegram' in result['message']
