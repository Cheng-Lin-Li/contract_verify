"""Auth router: login + current user (3-month scope · SKELETON)."""
from __future__ import annotations
from typing import Any


def login(payload: Any) -> Any:
    """POST /api/auth/login -> TokenResponse. Verify credentials, mint a JWT."""
    raise NotImplementedError


def me(current_user: Any = None) -> Any:
    """GET /api/auth/me -> UserOut for the authenticated caller."""
    raise NotImplementedError
