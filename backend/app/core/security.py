"""Authentication, password hashing and RBAC (3-month scope · SKELETON).

JWT-based stateless auth (FastAPI-Users style) with role checks. Bodies are
stubs; signatures define the security contract. Requires ``python-jose`` and
``passlib[bcrypt]`` (see requirements-3month.txt).
"""

from __future__ import annotations

from typing import Any

ROLE_HIERARCHY = ("operator", "gc_team", "attorney", "admin", "auditor")


def hash_password(plain: str) -> str:
    """Return a salted bcrypt hash of ``plain``."""
    raise NotImplementedError


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if ``plain`` matches the stored ``hashed`` value."""
    raise NotImplementedError


def create_access_token(subject: str, role: str, expires_minutes: int = 60) -> str:
    """Mint a signed JWT carrying the user id (``sub``) and ``role`` claim."""
    raise NotImplementedError


def decode_access_token(token: str) -> dict[str, Any]:
    """Verify and decode a JWT; raise on expiry/signature failure."""
    raise NotImplementedError


def role_allowed(user_role: str, allowed: tuple[str, ...]) -> bool:
    """Return True if ``user_role`` is in ``allowed`` (privilege check)."""
    raise NotImplementedError
