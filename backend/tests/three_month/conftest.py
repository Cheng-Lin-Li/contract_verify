"""Shared fixtures for the 3-month specs (only loaded under pytest)."""

from __future__ import annotations

import pytest


@pytest.fixture
def settings():
    """Settings with default thresholds for routing/SLA specs."""
    from app.config import get_settings, reset_settings_cache
    reset_settings_cache()
    return get_settings()


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    """A FastAPI TestClient over the real app with seeded demo users.

    Uses an isolated user store / reports dir so specs don't touch real data.
    Skips if the 3-month API deps (fastapi) aren't installed.
    """
    pytest.importorskip("fastapi")
    monkeypatch.setenv("USERS_DB_PATH", str(tmp_path / "users.json"))
    monkeypatch.setenv("REPORTS_DIR", str(tmp_path / "reports"))
    monkeypatch.setenv("UPLOADS_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("LLM_PROVIDER", "fake")  # upload runs the pipeline off-thread
    from app.config import reset_settings_cache
    reset_settings_cache()
    from app.api.auth_store import seed_demo_users
    seed_demo_users(reset=True)
    from fastapi.testclient import TestClient
    from app.api.app import create_app
    return TestClient(create_app())


@pytest.fixture
def auth_headers(api_client):
    """Bearer headers for the seeded attorney demo account."""
    resp = api_client.post("/api/auth/login",
                           json={"username": "attorney", "password": "attorney123"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def fake_embedder():
    """Deterministic embedder for retrieval specs."""
    class _E:
        def embed(self, texts):
            return [[float(len(t) % 7), 1.0, 0.0] for t in texts]
    return _E()


@pytest.fixture
def sample_contract():
    from app.core.enums import DocRole
    from app.core.models import CIRBlock, CIRDocument
    return CIRDocument(role=DocRole.CONTRACT, format="txt",
                       blocks=[CIRBlock(block_id="b-001", type="paragraph", page=1,
                                        text="Payment on net-45 day terms.")])


@pytest.fixture
def make_items_and_results():
    """Factory building (items, results) for routing specs."""
    from app.core.enums import Layer, Priority
    from app.core.models import ReferenceItem, VerificationResult

    def _make(critical_missing=False, playbook_violation=False, clean=False):
        items, results = [], []
        if clean:
            items.append(ReferenceItem(item_id="r-1", layer=Layer.REQUIREMENTS,
                                       text="x", priority=Priority.LOW))
            results.append(VerificationResult(item_id="r-1", layer=Layer.REQUIREMENTS,
                                              status="Covered", confidence=0.95))
        if critical_missing:
            items.append(ReferenceItem(item_id="r-2", layer=Layer.REQUIREMENTS,
                                       text="y", priority=Priority.CRITICAL))
            results.append(VerificationResult(item_id="r-2", layer=Layer.REQUIREMENTS,
                                              status="Missing", confidence=0.95))
        if playbook_violation:
            items.append(ReferenceItem(item_id="pb-1", layer=Layer.PLAYBOOK, text="z"))
            results.append(VerificationResult(item_id="pb-1", layer=Layer.PLAYBOOK,
                                              status="Violation", confidence=0.95))
        return items, results

    return _make


@pytest.fixture
def pg_dsn():
    """DSN for a throwaway Postgres (set PG_TEST_DSN to run)."""
    import os
    return os.environ.get("PG_TEST_DSN", "postgresql+asyncpg://localhost/cv_test")
