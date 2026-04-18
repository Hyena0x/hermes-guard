from hermes_guard.path_rules import canonicalize_path


def test_canonicalize_path_expands_and_normalizes(tmp_path):
    nested = tmp_path / 'a' / 'b'
    nested.mkdir(parents=True)
    target = nested / '..' / 'b'

    result = canonicalize_path(str(target))

    assert result == str(nested.resolve())
