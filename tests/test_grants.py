from hermes_guard.grants import add_grant, load_grants, revoke_grant


def test_add_and_load_persistent_grant(tmp_path):
    grants_path = tmp_path / 'guard-grants.yaml'

    grant = add_grant(
        grants_path,
        action='write',
        channel='cli',
        target_path='/tmp/demo.txt',
        lifetime='persistent',
    )

    grants = load_grants(grants_path)

    assert grant.id
    assert len(grants) == 1
    assert grants[0].id == grant.id
    assert grants[0].path == '/tmp/demo.txt'


def test_revoke_grant_removes_entry(tmp_path):
    grants_path = tmp_path / 'guard-grants.yaml'
    grant = add_grant(
        grants_path,
        action='read',
        channel='cli',
        target_path='/tmp/demo.txt',
        lifetime='persistent',
    )

    removed = revoke_grant(grants_path, grant.id)
    grants = load_grants(grants_path)

    assert removed is True
    assert grants == []
