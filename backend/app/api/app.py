"""FastAPI application factory (demo server implementation).

Builds the ASGI app, enables CORS for the SPA, and mounts the routers. Run with:
``uvicorn app.api.app:create_app --factory --reload`` (or ``scripts/run_api.py``).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routers import audit, auth, contracts, health, playbook, queue


def create_app() -> FastAPI:
    """Construct and return the configured FastAPI application."""
    settings = get_settings()
    app = FastAPI(title="contract_verify", version=settings.app_version)
    configure_cors(app)
    register_routers(app)
    return app


def configure_cors(app: FastAPI) -> None:
    """Enable CORS for the configured frontend origin(s)."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origin_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def register_routers(app: FastAPI) -> None:
    """Include every API router under the ``/api`` prefix."""
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(contracts.router, prefix="/api", tags=["contracts"])
    app.include_router(queue.router, prefix="/api/queue", tags=["queue"])
    app.include_router(playbook.router, prefix="/api/playbook", tags=["playbook"])
    app.include_router(audit.router, prefix="/api/audit", tags=["audit"])
