"""pytest configuration: ensure tests always run from the project root.

This lets you invoke pytest from either the repo root or the ``backend/``
subdirectory and get the same behaviour — resolving ``backend/prompts``,
``samples/``, and other root-relative paths correctly.
"""

from __future__ import annotations

import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
os.chdir(_PROJECT_ROOT)
os.environ.setdefault("LLM_PROVIDER", "fake")
os.environ.setdefault("PROMPTS_DIR", "backend/prompts")
os.environ.setdefault("LOG_LEVEL", "ERROR")
