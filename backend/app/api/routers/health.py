"""Health router: liveness/readiness."""

from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter()


@router.get("/health")
def health() -> dict:
    """Liveness probe."""
    return {"status": "ok", "version": get_settings().app_version}


@router.get("/ready")
def ready() -> dict:
    """Readiness probe (demo: always ready)."""
    return {"status": "ready"}
