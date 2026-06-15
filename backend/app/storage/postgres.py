"""PostgreSQL document/state store (3-month scope · SKELETON).

Implements the same interface as the MVP SQLite ``DocumentStore`` so a hybrid
deployment can keep state local in Postgres while blobs go to object storage.
Async SQLAlchemy; immutable audit via a BEFORE UPDATE/DELETE trigger.
Requires ``sqlalchemy[asyncio]`` + ``asyncpg``.
"""

from __future__ import annotations

from typing import Any, Optional


class PostgresDocumentStore:
    """Postgres-backed JSON state store (SKELETON)."""

    def __init__(self, dsn: str) -> None:
        raise NotImplementedError

    async def save(self, collection: str, key: str, value: dict[str, Any]) -> None:
        raise NotImplementedError

    async def load(self, collection: str, key: str) -> Optional[dict[str, Any]]:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError
