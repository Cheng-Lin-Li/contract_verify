"""FastAPI dependencies: auth, current user, and RBAC enforcement."""

from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.auth_store import User, get_user
from app.core.security import decode_access_token, role_allowed

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> User:
    """Resolve the authenticated user from a bearer token, or raise 401."""
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        claims = decode_access_token(creds.credentials)
    except Exception:  # jose.JWTError and friends
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = get_user(claims.get("sub", ""))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown user")
    return user


def require_role(*roles: str) -> Callable[..., User]:
    """Return a dependency that allows only the given roles (else 403)."""
    def _dep(user: User = Depends(get_current_user)) -> User:
        if not role_allowed(user.role, roles):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
        return user
    return _dep
