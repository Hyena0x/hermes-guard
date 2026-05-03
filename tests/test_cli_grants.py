from io import StringIO

from hermes_guard.cli import main
from hermes_guard.grants import load_grants


def test_guard_grant_creates_persistent_grant(tmp_path):
    grants_path = tmp_path / 'guard-grants.yaml'
    output = StringIO()

    exit_code = main(
        [
            'grant',
            '--channel', 'cli',
            '--action', 'read',
            '--path', '/tmp/demo.txt',
            '--lifetime', 'persistent',
            '--grants-path', str(grants_path),
        ],
        stdout=output,
    )

    grants = load_grants(grants_path)

    assert exit_code == 0
    assert len(grants) == 1
    assert grants[0].actions == ('read',)
    assert 'Grant created:' in output.getvalue()


def test_guard_grants_lists_active_grants(tmp_path):
    grants_path = tmp_path / 'guard-grants.yaml'
    main(
        [
            'grant',
            '--channel', 'cli',
            '--action', 'write',
            '--path', '/tmp/demo.txt',
            '--lifetime', 'persistent',
            '--grants-path', str(grants_path),
        ]
    )
    output = StringIO()

    exit_code = main(['grants', '--grants-path', str(grants_path)], stdout=output)

    assert exit_code == 0
    assert 'write' in output.getvalue()
    assert '/tmp/demo.txt' in output.getvalue()


def test_guard_revoke_removes_grant(tmp_path):
    grants_path = tmp_path / 'guard-grants.yaml'
    main(
        [
            'grant',
            '--channel', 'cli',
            '--action', 'patch',
            '--path', '/tmp/demo.txt',
            '--lifetime', 'persistent',
            '--grants-path', str(grants_path),
        ]
    )
    grant_id = load_grants(grants_path)[0].id
    output = StringIO()

    exit_code = main(
        ['revoke', '--id', grant_id, '--grants-path', str(grants_path)],
        stdout=output,
    )

    assert exit_code == 0
    assert load_grants(grants_path) == []
    assert 'Revoked grant' in output.getvalue()


def test_guard_revoke_returns_nonzero_for_missing_grant(tmp_path):
    grants_path = tmp_path / 'guard-grants.yaml'
    output = StringIO()

    exit_code = main(
        ['revoke', '--id', 'missing-grant', '--grants-path', str(grants_path)],
        stdout=output,
    )

    assert exit_code == 1
    assert 'Grant not found' in output.getvalue()


def test_guard_grant_rejects_session_grant_without_session_id(tmp_path):
    grants_path = tmp_path / 'guard-grants.yaml'
    output = StringIO()

    exit_code = main(
        [
            'grant',
            '--channel', 'cli',
            '--action', 'read',
            '--path', '/tmp/demo.txt',
            '--lifetime', 'session',
            '--grants-path', str(grants_path),
        ],
        stdout=output,
    )

    assert exit_code == 1
    assert load_grants(grants_path) == []
    assert 'Session grants require --session-id' in output.getvalue()
