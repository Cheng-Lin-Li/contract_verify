#!/usr/bin/env python3
"""Dependency-free test runner for contract_verify.

The production toolchain uses ``pytest`` (declared in ``backend/requirements.txt``).
This runner exists so the suite also passes in a minimal / air-gapped environment
where ``pytest`` is not installed: it discovers ``backend/tests/test_*.py``,
imports each module, and executes every top-level ``test_*`` function, reporting
pass/fail counts and exiting non-zero on any failure.

Both paths run the identical test functions; the tests use plain ``assert`` and
avoid pytest fixtures so they are portable across runners.

Usage:
    python run_tests.py            # run everything
    python run_tests.py scoring    # run only test files whose name matches "scoring"

Environment:
    The runner pins ``LLM_PROVIDER=fake`` so tests never reach a real model, sets
    the working directory to the repo root (so ``backend/prompts`` and ``samples``
    resolve), and puts ``backend`` on ``sys.path`` (so ``import app.*`` works).
"""

from __future__ import annotations

import importlib.util
import os
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
BACKEND = REPO_ROOT / "backend"
TESTS_DIR = BACKEND / "tests"


def _bootstrap() -> None:
    """Configure cwd, sys.path and env so tests resolve their dependencies."""
    os.chdir(REPO_ROOT)
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    os.environ.setdefault("LLM_PROVIDER", "fake")
    os.environ.setdefault("RETRIEVER", "direct")  # hermetic: no vector service needed
    os.environ.setdefault("LOG_LEVEL", "ERROR")  # keep test output readable


def _load_module(path: Path):
    """Import a test file as a standalone module."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv: list[str]) -> int:
    """Discover and run all matching test functions; return a process exit code."""
    _bootstrap()
    pattern = argv[1] if len(argv) > 1 else ""
    files = sorted(p for p in TESTS_DIR.glob("test_*.py") if pattern in p.name)

    passed = failed = 0
    failures: list[str] = []
    for f in files:
        mod = _load_module(f)
        tests = [(n, fn) for n, fn in vars(mod).items()
                 if n.startswith("test_") and callable(fn)]
        for name, fn in sorted(tests):
            try:
                fn()
                passed += 1
                print(f"  PASS {f.name}::{name}")
            except Exception:  # noqa: BLE001 - report any test failure
                failed += 1
                failures.append(f"{f.name}::{name}\n{traceback.format_exc()}")
                print(f"  FAIL {f.name}::{name}")

    print("\n" + "=" * 60)
    print(f"  {passed} passed, {failed} failed")
    print("=" * 60)
    if failures:
        print("\nFAILURES:\n")
        for fail in failures:
            print(fail)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
