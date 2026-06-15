"""TDD spec: Postgres state store (app/storage/postgres.py)."""

from __future__ import annotations

import pytest

pytest.importorskip("sqlalchemy")

from app.storage.postgres import PostgresDocumentStore
from tests.three_month._spec import skip_until_implemented


@skip_until_implemented
@pytest.mark.asyncio
async def test_save_load_roundtrip(pg_dsn):
    store = PostgresDocumentStore(pg_dsn)
    await store.save("reports", "c-1", {"coverage": 90.0})
    assert (await store.load("reports", "c-1"))["coverage"] == 90.0
    await store.close()


@skip_until_implemented
@pytest.mark.asyncio
async def test_load_missing_returns_none(pg_dsn):
    store = PostgresDocumentStore(pg_dsn)
    assert await store.load("reports", "nope") is None
    await store.close()
