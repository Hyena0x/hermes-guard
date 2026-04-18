from pathlib import Path

from hermes_guard.restore_points import load_latest_restore_point
from hermes_guard.update_manager import (
    apply_tag,
    create_restore_point,
    get_update_status,
    is_git_repo,
    list_tags,
    rollback_to_latest_restore_point,
)


def _init_git_repo(repo: Path) -> None:
    import subprocess

    subprocess.run(['git', 'init'], cwd=repo, check=True, capture_output=True)
    subprocess.run(['git', 'config', 'user.name', 'Hermes Guard Tests'], cwd=repo, check=True, capture_output=True)
    subprocess.run(['git', 'config', 'user.email', 'guard@example.com'], cwd=repo, check=True, capture_output=True)
    (repo / 'README.md').write_text('hello\n', encoding='utf-8')
    subprocess.run(['git', 'add', 'README.md'], cwd=repo, check=True, capture_output=True)
    subprocess.run(['git', 'commit', '-m', 'init'], cwd=repo, check=True, capture_output=True)


def test_is_git_repo_false_for_plain_directory(tmp_path):
    assert is_git_repo(tmp_path) is False



def test_is_git_repo_true_when_dot_git_exists(tmp_path):
    (tmp_path / '.git').mkdir()
    assert is_git_repo(tmp_path) is True



def test_list_tags_returns_most_recent_tags_first(tmp_path):
    import subprocess

    repo = tmp_path / 'repo'
    repo.mkdir()
    _init_git_repo(repo)
    subprocess.run(['git', 'tag', 'v2026.4.10'], cwd=repo, check=True, capture_output=True)
    subprocess.run(['git', 'tag', 'v2026.4.12'], cwd=repo, check=True, capture_output=True)

    tags = list_tags(repo)

    assert tags[:2] == ['v2026.4.12', 'v2026.4.10']



def test_get_update_status_reports_git_state(tmp_path):
    import subprocess

    repo = tmp_path / 'repo'
    repo.mkdir()
    _init_git_repo(repo)
    subprocess.run(['git', 'tag', 'v2026.4.12'], cwd=repo, check=True, capture_output=True)

    status = get_update_status(repo)

    assert status['is_git_repo'] is True
    assert status['dirty'] is False
    assert status['commit']
    assert status['tag'] == 'v2026.4.12'



def test_get_update_status_reports_non_git_repo_cleanly(tmp_path):
    status = get_update_status(tmp_path)

    assert status['is_git_repo'] is False
    assert status['error'] == 'not-a-git-repo'



def test_create_restore_point_writes_json_and_freeze_file(tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    _init_git_repo(repo)
    restore_dir = tmp_path / 'restore-points'

    restore_point = create_restore_point(repo, restore_dir=restore_dir)
    loaded = load_latest_restore_point(restore_dir)

    assert restore_point['repo_path'] == str(repo)
    assert Path(restore_point['pip_freeze_path']).exists()
    assert 'python_version' in restore_point
    assert loaded is not None
    assert loaded['git_commit'] == restore_point['git_commit']



def test_apply_tag_aborts_on_dirty_repo_by_default(tmp_path):
    import subprocess

    repo = tmp_path / 'repo'
    repo.mkdir()
    _init_git_repo(repo)
    subprocess.run(['git', 'tag', 'v2026.4.12'], cwd=repo, check=True, capture_output=True)
    (repo / 'README.md').write_text('dirty\n', encoding='utf-8')

    try:
        apply_tag(repo, 'v2026.4.12', restore_dir=tmp_path / 'restore-points')
    except ValueError as exc:
        assert str(exc) == 'dirty-working-tree'
    else:
        raise AssertionError('expected dirty-working-tree error')



def test_apply_tag_checks_out_tag_and_creates_restore_point(tmp_path):
    import subprocess

    repo = tmp_path / 'repo'
    repo.mkdir()
    _init_git_repo(repo)
    subprocess.run(['git', 'tag', 'v2026.4.10'], cwd=repo, check=True, capture_output=True)
    (repo / 'README.md').write_text('second\n', encoding='utf-8')
    subprocess.run(['git', 'commit', '-am', 'second'], cwd=repo, check=True, capture_output=True)
    subprocess.run(['git', 'tag', 'v2026.4.12'], cwd=repo, check=True, capture_output=True)

    result = apply_tag(repo, 'v2026.4.10', restore_dir=tmp_path / 'restore-points')
    head_tag = subprocess.run(
        ['git', 'describe', '--tags', '--exact-match'],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    assert result['applied_tag'] == 'v2026.4.10'
    assert result['restore_point']['git_tag'] == 'v2026.4.12'
    assert head_tag == 'v2026.4.10'



def test_rollback_to_latest_restore_point_restores_previous_tag(tmp_path):
    import subprocess

    repo = tmp_path / 'repo'
    repo.mkdir()
    _init_git_repo(repo)
    subprocess.run(['git', 'tag', 'v2026.4.10'], cwd=repo, check=True, capture_output=True)
    (repo / 'README.md').write_text('second\n', encoding='utf-8')
    subprocess.run(['git', 'commit', '-am', 'second'], cwd=repo, check=True, capture_output=True)
    subprocess.run(['git', 'tag', 'v2026.4.12'], cwd=repo, check=True, capture_output=True)
    restore_dir = tmp_path / 'restore-points'

    apply_tag(repo, 'v2026.4.10', restore_dir=restore_dir)
    result = rollback_to_latest_restore_point(repo, restore_dir=restore_dir)
    head_tag = subprocess.run(
        ['git', 'describe', '--tags', '--exact-match'],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    assert result['restored_ref'] == 'v2026.4.12'
    assert head_tag == 'v2026.4.12'



def test_rollback_to_latest_restore_point_errors_when_missing(tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    _init_git_repo(repo)

    try:
        rollback_to_latest_restore_point(repo, restore_dir=tmp_path / 'restore-points')
    except ValueError as exc:
        assert str(exc) == 'no-restore-point'
    else:
        raise AssertionError('expected no-restore-point error')
