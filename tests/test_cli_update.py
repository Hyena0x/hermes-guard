from io import StringIO

from hermes_guard.cli import main


def _init_git_repo(repo):
    import subprocess

    subprocess.run(['git', 'init'], cwd=repo, check=True, capture_output=True)
    subprocess.run(['git', 'config', 'user.name', 'Hermes Guard Tests'], cwd=repo, check=True, capture_output=True)
    subprocess.run(['git', 'config', 'user.email', 'guard@example.com'], cwd=repo, check=True, capture_output=True)
    (repo / 'README.md').write_text('hello\n', encoding='utf-8')
    subprocess.run(['git', 'add', 'README.md'], cwd=repo, check=True, capture_output=True)
    subprocess.run(['git', 'commit', '-m', 'init'], cwd=repo, check=True, capture_output=True)


def test_guard_update_status_prints_repo_state(tmp_path):
    import subprocess

    repo = tmp_path / 'repo'
    repo.mkdir()
    _init_git_repo(repo)
    subprocess.run(['git', 'tag', 'v2026.4.12'], cwd=repo, check=True, capture_output=True)
    output = StringIO()

    exit_code = main(['update', 'status', '--repo-path', str(repo)], stdout=output)

    text = output.getvalue()
    assert exit_code == 0
    assert 'is_git_repo: True' in text
    assert 'tag: v2026.4.12' in text


def test_guard_update_list_prints_tags(tmp_path):
    import subprocess

    repo = tmp_path / 'repo'
    repo.mkdir()
    _init_git_repo(repo)
    subprocess.run(['git', 'tag', 'v2026.4.10'], cwd=repo, check=True, capture_output=True)
    subprocess.run(['git', 'tag', 'v2026.4.12'], cwd=repo, check=True, capture_output=True)
    output = StringIO()

    exit_code = main(['update', 'list', '--repo-path', str(repo)], stdout=output)

    text = output.getvalue()
    assert exit_code == 0
    assert 'v2026.4.12' in text
    assert 'v2026.4.10' in text


def test_guard_update_checkpoint_writes_restore_point(tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    _init_git_repo(repo)
    restore_dir = tmp_path / 'restore-points'
    output = StringIO()

    exit_code = main(
        ['update', 'checkpoint', '--repo-path', str(repo), '--restore-dir', str(restore_dir)],
        stdout=output,
    )

    assert exit_code == 0
    assert any(restore_dir.glob('*.json'))
    assert 'Restore point created at' in output.getvalue()



def test_guard_update_apply_aborts_on_dirty_repo(tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    _init_git_repo(repo)
    import subprocess
    subprocess.run(['git', 'tag', 'v2026.4.12'], cwd=repo, check=True, capture_output=True)
    (repo / 'README.md').write_text('dirty\n', encoding='utf-8')
    output = StringIO()

    exit_code = main(['update', 'apply', '--tag', 'v2026.4.12', '--repo-path', str(repo)], stdout=output)

    assert exit_code == 1
    assert 'dirty-working-tree' in output.getvalue()



def test_guard_update_apply_checks_out_tag(tmp_path):
    import subprocess

    repo = tmp_path / 'repo'
    repo.mkdir()
    _init_git_repo(repo)
    subprocess.run(['git', 'tag', 'v2026.4.10'], cwd=repo, check=True, capture_output=True)
    (repo / 'README.md').write_text('second\n', encoding='utf-8')
    subprocess.run(['git', 'commit', '-am', 'second'], cwd=repo, check=True, capture_output=True)
    subprocess.run(['git', 'tag', 'v2026.4.12'], cwd=repo, check=True, capture_output=True)
    restore_dir = tmp_path / 'restore-points'
    output = StringIO()

    exit_code = main(
        ['update', 'apply', '--tag', 'v2026.4.10', '--repo-path', str(repo), '--restore-dir', str(restore_dir)],
        stdout=output,
    )
    head_tag = subprocess.run(
        ['git', 'describe', '--tags', '--exact-match'],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    assert exit_code == 0
    assert head_tag == 'v2026.4.10'
    assert 'Applied tag v2026.4.10' in output.getvalue()



def test_guard_update_rollback_restores_latest_restore_point(tmp_path):
    import subprocess

    repo = tmp_path / 'repo'
    repo.mkdir()
    _init_git_repo(repo)
    subprocess.run(['git', 'tag', 'v2026.4.10'], cwd=repo, check=True, capture_output=True)
    (repo / 'README.md').write_text('second\n', encoding='utf-8')
    subprocess.run(['git', 'commit', '-am', 'second'], cwd=repo, check=True, capture_output=True)
    subprocess.run(['git', 'tag', 'v2026.4.12'], cwd=repo, check=True, capture_output=True)
    restore_dir = tmp_path / 'restore-points'
    main(['update', 'apply', '--tag', 'v2026.4.10', '--repo-path', str(repo), '--restore-dir', str(restore_dir)])
    output = StringIO()

    exit_code = main(
        ['update', 'rollback', '--repo-path', str(repo), '--restore-dir', str(restore_dir)],
        stdout=output,
    )
    head_tag = subprocess.run(
        ['git', 'describe', '--tags', '--exact-match'],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    assert exit_code == 0
    assert head_tag == 'v2026.4.12'
    assert 'Rolled back to v2026.4.12' in output.getvalue()
