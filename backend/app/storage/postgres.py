"""PostgreSQL document/state store (3-month scope).

Implements the same interface as the MVP SQLite ``DocumentStore`` so a hybrid
deployment can keep state local in Postgres while blobs go to object storage.
Async SQLAlchemy (asyncpg driver). JSON state lives in a ``documents`` table;
the audit trail lives in an append-only ``audit_events`` table protected by a
``BEFORE UPDATE OR DELETE`` trigger that rejects any mutation — so the immutable
audit guarantee is enforced by the database, not just by convention.

Requires ``sqlalchemy[asyncio]`` + ``asyncpg``.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS documents (
        collection text NOT NULL,
        key        text NOT NULL,
        value      jsonb NOT NULL,
        updated_at timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (collection, key)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_events (
        event_id    text PRIMARY KEY,
        occurred_at timestamptz NOT NULL DEFAULT now(),
        doc_id      text,
        event       jsonb NOT NULL
    )
    """,
    """
    CREATE OR REPLACE FUNCTION cv_block_mutation() RETURNS trigger AS $$
    BEGIN
        RAISE EXCEPTION 'audit_events is append-only; % is not permitted', TG_OP;
    END;
    $$ LANGUAGE plpgsql
    """,
    "DROP TRIGGER IF EXISTS cv_audit_immutable ON audit_events",
    """
    CREATE TRIGGER cv_audit_immutable
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION cv_block_mutation()
    """,
)


class PostgresDocumentStore:
    """Postgres-backed JSON state store with an immutable audit table."""

    def __init__(self, dsn: str) -> None:
        """Create the async engine (no connection until first use)."""
        self._engine: AsyncEngine = create_async_engine(dsn, future=True)
        self._schema_ready = False

    async def _ensure_schema(self) -> None:
        """Create the tables/trigger once per process."""
        if self._schema_ready:
            return
        async with self._engine.begin() as conn:
            for stmt in _SCHEMA:
                await conn.execute(text(stmt))
        self._schema_ready = True

    async def save(self, collection: str, key: str, value: dict[str, Any]) -> None:
        """Upsert a JSON ``value`` under ``(collection, key)``."""
        await self._ensure_schema()
        async with self._engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO documents (collection, key, value, updated_at) "
                    "VALUES (:c, :k, CAST(:v AS jsonb), now()) "
                    "ON CONFLICT (collection, key) "
                    "DO UPDATE SET value = EXCLUDED.value, updated_at = now()"
                ),
                {"c": collection, "k": key, "v": json.dumps(value, default=str)},
            )

    async def load(self, collection: str, key: str) -> Optional[dict[str, Any]]:
        """Return the JSON value under ``(collection, key)`` or ``None``."""
        await self._ensure_schema()
        async with self._engine.connect() as conn:
            row = (await conn.execute(
                text("SELECT value FROM documents WHERE collection = :c AND key = :k"),
                {"c": collection, "k": key},
            )).first()
        if row is None:
            return None
        value = row[0]
        return json.loads(value) if isinstance(value, str) else value

    async def append_audit(self, event: dict[str, Any], *,
                           doc_id: Optional[str] = None) -> str:
        """Append one immutable audit event; return its event_id."""
        await self._ensure_schema()
        event_id = event.get("event_id") or str(uuid.uuid4())
        async with self._engine.begin() as conn:
            await conn.execute(
                text("INSERT INTO audit_events (event_id, doc_id, event) "
                     "VALUES (:id, :doc, CAST(:e AS jsonb))"),
                {"id": event_id, "doc": doc_id, "e": json.dumps(event, default=str)},
            )
        return event_id

    async def read_audit(self, doc_id: str) -> list[dict[str, Any]]:
        """Return audit events for ``doc_id`` in write order."""
        await self._ensure_schema()
        async with self._engine.connect() as conn:
            rows = (await conn.execute(
                text("SELECT event FROM audit_events WHERE doc_id = :d "
                     "ORDER BY occurred_at"),
                {"d": doc_id},
            )).all()
        return [json.loads(r[0]) if isinstance(r[0], str) else r[0] for r in rows]

    async def close(self) -> None:
        """Dispose the engine and its connection pool."""
        await self._engine.dispose()
