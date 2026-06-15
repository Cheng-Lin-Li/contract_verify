"""FastAPI dependencies: auth, current user, and RBAC enforcement (SKELETON)."""

from __future__ import annotations

from typing import Any, Callable


def get_current_user(token: str | None = None) -> Any:
    """Resolve and return the authenticated user from a bearer token.

    Raises:
        HTTPException 401: if the token is missing or invalid.
    """
    raise NotImplementedError


def require_role(*roles: str) -> Callable[..., Any]:
    """Return a dependency that allows only the given roles.

    Example:
        ``@router.get(..., dependencies=[Depends(require_role("attorney"))])``

    Raises:
        HTTPException 403: if the current user's role is not permitted.
    """
    raise NotImplementedError


def get_db() -> Any:
    """Yield a database session (async), closing it on request teardown."""
    raise NotImplementedError
