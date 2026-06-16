"""Authentication, password hashing and RBAC (demo server implementation).

JWT-based stateless auth with role checks. Uses ``passlib[bcrypt]`` for hashing
and ``python-jose`` for tokens (both in requirements-3month.txt). The signing
key and token lifetime come from settings (``SECRET_KEY`` / ``JWT_*``).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt as _bcrypt

from app.config import get_settings

# Role order is informational; access checks use explicit allow-lists, not rank.
ROLE_HIERARCHY = ("operator", "gc_team", "attorney", "admin", "auditor")


def hash_password(plain: str) -> str:
    """Return a salted bcrypt hash of ``plain``."""
    return _bcrypt.hashpw(plain.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if ``plain`` matches the stored ``hashed`` value."""
    try:
        return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, role: str, expires_minutes: int | None = None) -> str:
    """Mint a signed JWT carrying the user id (``sub``) and ``role`` claim."""
    from jose import jwt

    s = get_settings()
    minutes = expires_minutes if expires_minutes is not None else s.jwt_expire_minutes
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
    }
    return jwt.encode(payload, s.secret_key, algorithm=s.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Verify and decode a JWT; raise ``JWTError`` on expiry/signature failure."""
    from jose import jwt

    s = get_settings()
    return jwt.decode(token, s.secret_key, algorithms=[s.jwt_algorithm])


def role_allowed(user_role: str, allowed: tuple[str, ...]) -> bool:
    """Return True if ``user_role`` is in ``allowed`` (privilege check)."""
    return user_role in allowed
