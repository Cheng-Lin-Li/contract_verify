"""File-backed user store for the demo server.

A deliberately simple JSON store (``USERS_DB_PATH``) so the demo runs without a
database. Passwords are bcrypt-hashed via :mod:`app.core.security`. Production
deployments replace this with the Postgres-backed user table (3-month scope).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.config import get_settings
from app.core.security import hash_password, verify_password

# Demo accounts created by ``scripts/seed_demo.py`` (documented in the README).
DEMO_USERS = [
    {"username": "operator", "password": "operator123", "role": "operator"},
    {"username": "attorney", "password": "attorney123", "role": "attorney"},
    {"username": "admin", "password": "admin123", "role": "admin"},
]


@dataclass
class User:
    id: str
    username: str
    role: str


def _db_path() -> Path:
    return Path(get_settings().users_db_path)


def _load() -> dict[str, dict]:
    p = _db_path()
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _save(users: dict[str, dict]) -> None:
    p = _db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(users, indent=2), encoding="utf-8")


def create_user(username: str, password: str, role: str) -> User:
    """Create (or overwrite) a user with a hashed password."""
    users = _load()
    users[username] = {
        "id": users.get(username, {}).get("id") or os.urandom(8).hex(),
        "username": username,
        "role": role,
        "password_hash": hash_password(password),
    }
    _save(users)
    rec = users[username]
    return User(id=rec["id"], username=username, role=role)


def authenticate(username: str, password: str) -> Optional[User]:
    """Return the user if the password matches, else ``None``."""
    rec = _load().get(username)
    if not rec or not verify_password(password, rec["password_hash"]):
        return None
    return User(id=rec["id"], username=rec["username"], role=rec["role"])


def get_user(username: str) -> Optional[User]:
    rec = _load().get(username)
    return User(id=rec["id"], username=rec["username"], role=rec["role"]) if rec else None


def seed_demo_users(reset: bool = False) -> list[User]:
    """Create the demo accounts. With ``reset`` the store is cleared first."""
    if reset and _db_path().exists():
        _db_path().unlink()
    created = [create_user(u["username"], u["password"], u["role"]) for u in DEMO_USERS]
    return created
