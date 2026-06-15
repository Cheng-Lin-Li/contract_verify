"""TDD spec: auth endpoints (app/api/routers/auth.py)."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from tests.three_month._spec import skip_until_implemented


@skip_until_implemented
def test_login_returns_token(api_client):
    resp = api_client.post("/api/auth/login",
                           json={"username": "attorney", "password": "pw"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer" and body["access_token"]


@skip_until_implemented
def test_login_rejects_bad_credentials(api_client):
    resp = api_client.post("/api/auth/login",
                           json={"username": "x", "password": "y"})
    assert resp.status_code == 401


@skip_until_implemented
def test_me_requires_auth(api_client):
    assert api_client.get("/api/auth/me").status_code == 401
