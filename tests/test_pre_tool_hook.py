import hermes_guard.pre_tool_hook as hook
from hermes_guard.models import Decision


def test_pre_tool_check_fails_closed_on_internal_error(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError('boom')

    monkeypatch.setattr(hook, 'evaluate_policy', boom)

    decision = hook.pre_tool_check(tool_name='read_file', args={'path': '/tmp/x'})

    assert decision.decision == Decision.CONFIRM
    assert decision.rule_id == 'guard-internal-error'
