"""FastAPI application factory (3-month scope · SKELETON).

Builds the ASGI app, mounts routers, and wires middleware (CORS, auth, request
logging). Every handler is a stub raising ``NotImplementedError``; this module
defines the wiring contract, not the behaviour.

Run (once implemented): ``uvicorn app.api.app:create_app --factory --reload``.
Requires ``fastapi`` + ``uvicorn`` (see requirements-3month.txt).
"""

from __future__ import annotations

from typing import Any


def create_app() -> Any:
    """Construct and return the configured FastAPI application.

    Responsibilities (to implement):
        * instantiate ``FastAPI(title=..., version=settings.app_version)``,
        * add CORS for the frontend origin,
        * include the routers from :mod:`app.api.routers`,
        * attach the deployment-residency check at startup,
        * register structured request logging + exception handlers.

    Returns:
        A FastAPI instance.
    """
    raise NotImplementedError("3-month: build the FastAPI app and mount routers")


def register_routers(app: Any) -> None:
    """Include every API router on ``app`` under the ``/api`` prefix."""
    raise NotImplementedError


def configure_cors(app: Any) -> None:
    """Enable CORS for the configured frontend origin(s)."""
    raise NotImplementedError


def configure_logging_middleware(app: Any) -> None:
    """Add middleware that logs each request with duration and request id."""
    raise NotImplementedError
