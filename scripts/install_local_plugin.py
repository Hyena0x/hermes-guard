#!/usr/bin/env python3
"""Prepare a local Hermes Guard plugin directory for manual testing.

This script writes the minimal Hermes directory-plugin files expected by Hermes.
It does not modify shell rc files or launch Hermes automatically.
"""

from __future__ import annotations

import argparse
from pathlib import Path

PLUGIN_YAML = """name: hermes_guard
version: 0.1.0
description: Hermes Guard pre-tool policy plugin
provides_hooks:
  - pre_tool_call
"""

INIT_PY = "from hermes_guard.plugin_entry import register\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare a local Hermes Guard plugin directory")
    parser.add_argument(
        "--target",
        default="~/.hermes/plugins/hermes_guard",
        help="Plugin directory to write (default: ~/.hermes/plugins/hermes_guard)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    target = Path(args.target).expanduser()
    target.mkdir(parents=True, exist_ok=True)
    (target / "plugin.yaml").write_text(PLUGIN_YAML, encoding="utf-8")
    (target / "__init__.py").write_text(INIT_PY, encoding="utf-8")

    print(f"Wrote Hermes Guard plugin files to: {target}")
    print("Next steps:")
    print("  1. Export PYTHONPATH to include this repo")
    print("  2. Export HERMES_GUARD_POLICY_PATH and HERMES_GUARD_GRANTS_PATH")
    print("  3. Start Hermes and verify pre-tool blocking behavior")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
