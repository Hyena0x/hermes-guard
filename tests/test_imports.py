from hermes_guard import __version__
from hermes_guard.cli import build_parser
from hermes_guard.models import Decision


def test_package_version_exists():
    assert __version__ == '0.1.0'


def test_decision_enum_values_are_minimal():
    assert [member.value for member in Decision] == ['allow', 'deny', 'confirm']


def test_cli_has_guard_surface():
    parser = build_parser()
    actions = [action.dest for action in parser._actions]
    assert 'command' in actions
