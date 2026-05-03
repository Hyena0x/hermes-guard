from pathlib import Path

import yaml

from hermes_guard.models import Decision
from hermes_guard.policy import evaluate_policy

EXAMPLE_POLICY = Path(__file__).resolve().parents[1] / 'examples' / 'guard-policy.yaml'



def _materialize_example_policy(tmp_path):
    raw = EXAMPLE_POLICY.read_text(encoding='utf-8')
    workspace = tmp_path / 'workspace'
    rendered = raw.replace('/path/to/workspace', str(workspace))
    policy_path = tmp_path / 'guard-policy.yaml'
    policy_path.write_text(rendered, encoding='utf-8')
    return policy_path, workspace

def test_example_policy_uses_generic_workspace_path():
    data = yaml.safe_load(EXAMPLE_POLICY.read_text(encoding='utf-8'))

    assert data['rules'][0]['path'] == '/path/to/workspace/**'

def test_example_policy_includes_execute_in_workspace_rule():
    data = yaml.safe_load(EXAMPLE_POLICY.read_text(encoding='utf-8'))

    assert 'execute' in data['rules'][0]['action']

def test_example_policy_allows_safe_terminal_in_workspace(tmp_path):
    policy_path, workspace = _materialize_example_policy(tmp_path)
    workspace.mkdir()

    decision = evaluate_policy(
        tool_name='terminal',
        args={'command': 'git status', 'workdir': str(workspace)},
        channel='cli',
        policy_path=policy_path,
    )

    assert decision.decision == Decision.ALLOW

def test_example_policy_denies_env_files_inside_workspace(tmp_path):
    policy_path, workspace = _materialize_example_policy(tmp_path)
    env_file = workspace / '.env'
    env_file.parent.mkdir(parents=True)
    env_file.write_text('SECRET=1\n', encoding='utf-8')

    decision = evaluate_policy(
        tool_name='read_file',
        args={'path': str(env_file)},
        channel='cli',
        policy_path=policy_path,
    )

    assert decision.decision == Decision.DENY
