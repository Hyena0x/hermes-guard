"""Path normalization and matching helpers.

Implementation is intentionally minimal for the project skeleton.
Real rule resolution will be added incrementally.
"""

from __future__ import annotations

import os
from pathlib import Path


def canonicalize_path(path: str) -> str:
    """Return a canonical real path for matching.

    This is a hard requirement in the v0.1 spec.
    """
    expanded = os.path.expanduser(path)
    absolute = os.path.abspath(expanded)
    real = os.path.realpath(absolute)
    return str(Path(real))
