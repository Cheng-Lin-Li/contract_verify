"""Health router: liveness/readiness (3-month · SKELETON)."""
from __future__ import annotations
from typing import Any


def health() -> Any:
    """GET /api/health -> {"status": "ok", "version": ...}. Liveness probe."""
    raise NotImplementedError


def ready() -> Any:
    """GET /api/ready -> readiness: DB, vector store and LLM reachable."""
    raise NotImplementedError
