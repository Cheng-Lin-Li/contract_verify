"""TDD helpers for the 3-month feature specs.

These tests are written *first* (test-driven development) and describe the
intended behaviour of the 3-month backend. They are collected but **skipped by
default** until the corresponding feature is implemented; run them while
implementing with ``RUN_3MONTH=1 pytest backend/tests/three_month``.

The bundled ``run_tests.py`` does not scan this subfolder, so the MVP suite
stays green.
"""

from __future__ import annotations

import os

try:
    import pytest

    _RUN = os.environ.get("RUN_3MONTH") == "1"
    skip_until_implemented = pytest.mark.skipif(
        not _RUN,
        reason="3-month feature spec (TDD): implementation pending. Set RUN_3MONTH=1 to run.",
    )
except ImportError:  # pragma: no cover - allows import without pytest
    def skip_until_implemented(fn):  # type: ignore
        return fn
